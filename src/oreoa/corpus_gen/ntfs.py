"""Raw NTFS disk image generator v0 (locked decision 5: no mounting).

Pipeline per scenario:

1. ``build_plan`` derives the root-level file plan from the ``file`` events
   (``on_image: true``) - deterministic bodies, sorted names.
2. ``run_container`` executes the one-shot pinned container
   (``oreoa/corpus-ntfs``, debian-slim + ntfs-3g at ``NTFS3G_VERSION``):
   ``mkntfs --force -Q`` on a sparse file + ``ntfscp`` for every file. No
   privileged container, no mount - ntfs tools work on regular files.
3. ``patch_image`` (host-side, pure Python) makes the result deterministic
   and plants the timestomping:
   - boot-sector serial (primary + backup) set to a scenario-derived value;
   - every matched file gets its $STANDARD_INFORMATION and $FILE_NAME
     timestamps written from the scenario (``si_created``/``si_modified``
     forge the SI set - H-AF-003);
   - every other in-use MFT record (and the root $INDEX_ROOT entries) is
     blanket-normalized to the scenario window start (mkntfs/ntfscp write
     wall-clock times otherwise);
   - $LogFile and $UsnJrnl:$J data runs are zeroed (journaling noise);
   - $MFTMirr first records are rewritten from the patched $MFT.

Limitation v0 (journalized): files land at the image root (ntfs-3g has no
mkfs-side mkdir); the full directory tree stays declarative in MFT.csv
(``kape.py``) and is exercised by the deep-lane image parsing (step 4).

The patcher also provides ``read_entries`` used by tests to verify the
planted SI/FN skew without any mount.
"""

from __future__ import annotations

import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from oreoa.corpus_gen.scenario import FileArtifact, Scenario
from oreoa.corpus_gen.velociraptor import file_body

IMAGE_SIZE_MB = 64
EPOCH_DELTA_S = 11_644_473_600
FT_HUNDRED_NS = 10_000_000


def filetime_to_datetime(value: int) -> datetime:
    return datetime.fromtimestamp(value / FT_HUNDRED_NS - EPOCH_DELTA_S, tz=timezone.utc).replace(tzinfo=None)


def datetime_to_filetime(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int((value.timestamp() + EPOCH_DELTA_S) * FT_HUNDRED_NS)


def build_plan(scenario: Scenario) -> list[dict]:
    """Root-level files for the image: {name, body(bytes)} - deterministic.

    The host stages the bodies (the one-shot image has no python/xxd); the
    container only runs mkntfs + ntfscp (see ``write_staging``).
    """
    plan = []
    for event in scenario.expand_events():
        if isinstance(event, FileArtifact) and event.on_image:
            name = event.path.replace("/", "\\").rsplit("\\", 1)[-1]
            plan.append({"name": name, "body": file_body(event, scenario)})
    plan.sort(key=lambda entry: entry["name"])
    names = [entry["name"] for entry in plan]
    if len(names) != len(set(names)):
        raise ValueError("on_image files must have unique basenames at image root (v0 limitation)")
    return plan


def write_staging(work_dir: Path, plan: list[dict]) -> Path:
    """Stage file bodies + plan.txt (name<TAB>srcfile) for the container."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for index, entry in enumerate(plan):
        src = f".src_{index}"
        (work_dir / src).write_bytes(entry["body"])
        lines.append(f"{entry['name']}\t{src}")
    (work_dir / "plan.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return work_dir / "plan.txt"


def clean_staging(work_dir: Path) -> None:
    work_dir = Path(work_dir)
    (work_dir / "plan.txt").unlink(missing_ok=True)
    for path in work_dir.glob(".src_*"):
        path.unlink(missing_ok=True)


def container_command(image: str, work_dir: Path, size_mb: int = IMAGE_SIZE_MB, out_name: str = "disk.img") -> list[str]:
    """docker one-shot command (pattern ClamAV S1.5: host stays clean)."""
    work_dir = Path(work_dir).resolve()
    return [
        "docker", "run", "--rm",
        "--user", f"{work_dir.stat().st_uid}:{work_dir.stat().st_gid}",
        "-v", f"{work_dir}:/work",
        image,
        str(size_mb),
        out_name,
    ]


def run_container(image: str, work_dir: Path, size_mb: int = IMAGE_SIZE_MB, out_name: str = "disk.img") -> None:
    """One-shot container: mkntfs + ntfscp from /work/plan.txt -> /work/<out>."""
    work_dir = Path(work_dir).resolve()
    image_path = work_dir / out_name
    image_path.unlink(missing_ok=True)
    result = subprocess.run(
        container_command(image, work_dir, size_mb, out_name),
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"corpus-ntfs container failed: {result.stderr.strip()}")
    # The daemon's writes can become visible to this process with a small
    # delay - wait actively instead of failing on the first stat.
    for _ in range(50):
        if image_path.is_file() and image_path.stat().st_size > 0:
            return
        time.sleep(0.2)
    raise RuntimeError(f"container reported success but {image_path} is not visible")


# ---------------------------------------------------------------------------
# MFT patcher
# ---------------------------------------------------------------------------

ATTR_SI = 0x10
ATTR_FN = 0x30
ATTR_INDEX_ROOT = 0x90
ATTR_DATA = 0x80


class _MftLayout:
    def __init__(self, buf: bytes) -> None:
        if buf[0x03:0x0B] != b"NTFS    ":
            raise ValueError("not an NTFS volume (bad OEM id)")
        self.bytes_per_sector = struct.unpack_from("<H", buf, 0x0B)[0]
        self.sectors_per_cluster = buf[0x0D]
        self.mft_lcn = struct.unpack_from("<Q", buf, 0x30)[0]
        self.mftmirr_lcn = struct.unpack_from("<Q", buf, 0x38)[0]
        clusters_per_mft = struct.unpack_from("<b", buf, 0x40)[0]
        self.mft_record_size = 2 ** (-clusters_per_mft) if clusters_per_mft < 0 else clusters_per_mft * self.sectors_per_cluster * self.bytes_per_sector
        self.mft_offset = self.mft_lcn * self.sectors_per_cluster * self.bytes_per_sector

    def cluster_offset(self, lcn: int) -> int:
        return lcn * self.sectors_per_cluster * self.bytes_per_sector


def _apply_fixup(record: bytearray, sector_size: int) -> list[bytes]:
    """Apply the update-sequence fixup; returns the array to restore on write."""
    usa_offset, usa_count = struct.unpack_from("<HH", record, 0x04)
    usa = [record[usa_offset + 2 * i : usa_offset + 2 * i + 2] for i in range(usa_count)]
    for i in range(1, usa_count):
        end = sector_size * i
        record[end - 2 : end] = usa[i]
    return usa


def _restore_fixup(record: bytearray, usa: list[bytes], sector_size: int) -> None:
    for i in range(1, len(usa)):
        end = sector_size * i
        record[end - 2 : end] = usa[i]


def _iter_attributes(record: bytearray, attrs_offset: int):
    offset = attrs_offset
    while offset + 16 <= len(record):
        attr_type, length = struct.unpack_from("<II", record, offset)
        if attr_type == 0xFFFFFFFF or length == 0:
            return
        yield offset, attr_type, length
        offset += length


def _read_attr_name(record: bytearray, offset: int) -> str:
    name_len = record[offset + 0x09]
    name_offset = struct.unpack_from("<H", record, offset + 0x0A)[0]
    if name_len == 0:
        return ""
    raw = record[name_offset : name_offset + 2 * name_len]
    return raw.decode("utf-16-le")


def _attr_value(record: bytearray, offset: int, attr_offset: int) -> tuple[int, int]:
    value_offset = struct.unpack_from("<H", record, offset + 0x14)[0]
    value_length = struct.unpack_from("<I", record, offset + 0x10)[0]
    return attr_offset + value_offset, value_length


def _patch_times(record: bytearray, attr_offset: int, filetime: int, value_skip: int = 0) -> None:
    """Write the 4 timestamps of an attribute value.

    ``value_skip``: bytes to skip inside the value before the timestamps -
    $STANDARD_INFORMATION starts with the times (0), $FILE_NAME starts with
    the parent reference (8).
    """
    value_offset, value_length = _attr_value(record, attr_offset, attr_offset)
    for i in range(4):
        struct.pack_into("<Q", record, value_offset + value_skip + 8 * i, filetime)


def _read_times(record: bytearray, attr_offset: int, value_skip: int = 0) -> list[int]:
    value_offset, _ = _attr_value(record, attr_offset, attr_offset)
    return [struct.unpack_from("<Q", record, value_offset + value_skip + 8 * i)[0] for i in range(4)]


def _fn_name(record: bytearray, attr_offset: int) -> tuple[str, int]:
    """Return (name, namespace) of a $FILE_NAME attribute value."""
    value_offset, _ = _attr_value(record, attr_offset, attr_offset)
    name_len = record[value_offset + 0x40]
    namespace = record[value_offset + 0x41]
    raw = record[value_offset + 0x42 : value_offset + 0x42 + 2 * name_len]
    return raw.decode("utf-16-le"), namespace


def _fn_parent(record: bytearray, attr_offset: int) -> int:
    value_offset, _ = _attr_value(record, attr_offset, attr_offset)
    return struct.unpack_from("<Q", record, value_offset)[0] & 0x0000FFFFFFFFFFFF


def _patch_index_root(record: bytearray, attr_offset: int, horizon_ft: int, base_ft: int, sector_size: int) -> None:
    """Normalize post-scenario wall-clock u64s inside a resident $INDEX_ROOT.

    Index entry streams vary by index type ($I30 FILE_NAME streams carry the
    times at +8; $Extend $O indexes differ) - any 8-byte slot above the
    horizon is a build wall-clock artifact and becomes base_ft; refs, sizes
    and flags are small and stay untouched.
    """
    value_offset, value_length = _attr_value(record, attr_offset, attr_offset)
    entries_offset = struct.unpack_from("<I", record, value_offset + 0x10)[0]
    total_size = struct.unpack_from("<I", record, value_offset + 0x14)[0]
    pos = value_offset + entries_offset
    end = value_offset + total_size
    while pos + 16 <= end:
        entry_length = struct.unpack_from("<H", record, pos + 0x08)[0]
        flags = struct.unpack_from("<H", record, pos + 0x0C)[0]
        # Sweep the whole entry body (stream_len is 0 for some index types,
        # e.g. $ObjId/$O whose timestamps sit deeper in the entry).
        body = min(entry_length if entry_length else end - pos, end - pos)
        if body > 0x10:
            _normalize_stream_slots(record, pos + 0x10, body - 0x10, horizon_ft, base_ft)
        if entry_length == 0 or flags & 0x02:
            break
        pos += entry_length


def _normalize_stream_slots(record: bytearray, stream_pos: int, stream_length: int, horizon_ft: int, base_ft: int) -> None:
    for slot in range(0, max(stream_length - 7, 0), 8):
        offset = stream_pos + slot
        if offset + 8 > len(record):
            return
        value = struct.unpack_from("<Q", record, offset)[0]
        if window_edge_check(value, horizon_ft):
            struct.pack_into("<Q", record, offset, base_ft)


def _patch_indx_buffers(buf: bytearray, layout: _MftLayout, horizon_ft: int, base_ft: int) -> int:
    """Normalize FILE_NAME timestamps inside $INDEX_ALLOCATION buffers (INDX).

    mkntfs spills the root directory index to non-resident $INDEX_ALLOCATION
    when the metafile set is large; those INDX buffers carry wall-clock
    timestamps. Only entries whose created-time looks like a post-scenario
    wall-clock value are touched (guard: $Secure/$Extend index entries have
    short key streams without FILE_NAME timestamps). Returns the count of
    patched buffers.
    """
    sector_size = layout.bytes_per_sector
    patched = 0
    pos = 0
    while True:
        pos = buf.find(b"INDX", pos)
        if pos < 0:
            break
        record = bytearray(buf[pos : pos + 4096])
        if len(record) < 512:
            pos += 1
            continue
        usa_offset, usa_count = struct.unpack_from("<HH", record, 0x04)
        if not (0 < usa_offset < 4096 and 1 < usa_count <= 9):
            pos += 4
            continue
        usa = _apply_fixup(record, sector_size)
        # Full-buffer slot sweep: INDX buffers hold only index entries (no
        # file content) and entry layouts vary by index type ($I30, $Secure,
        # $AttrDef) - every post-horizon u64 is a build wall-clock timestamp;
        # refs, sizes and fixup signatures are small and survive.
        _normalize_stream_slots(record, 0, len(record), horizon_ft, base_ft)
        _restore_fixup(record, usa, sector_size)
        buf[pos : pos + 4096] = record
        patched += 1
        pos += 4096
    return patched


def window_edge_check(value: int, horizon_ft: int) -> bool:
    """Post-scenario wall-clock timestamp (base_time normalization target)."""
    return horizon_ft < value


def _zero_nonresident_runs(image: bytearray, record: bytearray, attr_offset: int, layout: _MftLayout) -> None:
    """Zero the cluster runs of a non-resident attribute ($LogFile, $UsnJrnl:$J)."""
    runs_offset = struct.unpack_from("<H", record, attr_offset + 0x20)[0]
    pos = attr_offset + runs_offset
    cluster_size = layout.sectors_per_cluster * layout.bytes_per_sector
    lcn = 0
    while pos < len(record) and record[pos] != 0:
        header = record[pos]
        length_size = header & 0x0F
        offset_size = header >> 4
        pos += 1
        length = int.from_bytes(record[pos : pos + length_size], "little")
        pos += length_size
        if offset_size:
            raw = record[pos : pos + offset_size]
            delta = int.from_bytes(raw, "little", signed=True)
            lcn += delta
            pos += offset_size
        start = layout.cluster_offset(lcn)
        image[start : start + length * cluster_size] = b"\x00" * (length * cluster_size)


def patch_image(
    image_path: Path,
    entries: dict[str, dict[str, int]],
    base_time: datetime,
    serial: int,
    horizon_time: datetime | None = None,
) -> dict[str, list[int]]:
    """Patch the raw image in place (deterministic + timestomping).

    ``entries`` maps file basename (lowercase) -> {"si": filetime, "fn": filetime}.
    Returns matched entries: name -> [SI created, SI modified, FN created, FN modified]
    for verification.
    """
    buf = bytearray(Path(image_path).read_bytes())
    layout = _MftLayout(buf)
    sector_size = layout.bytes_per_sector
    base_ft = datetime_to_filetime(base_time)
    # Horizon = end of the scenario window: every timestamp above it is a
    # build wall-clock artifact and is normalized; scenario times (and the
    # 2019 timestomp) stay below it and are preserved.
    horizon_ft = datetime_to_filetime(horizon_time or base_time)
    matched: dict[str, list[int]] = {}
    mft_records: list[tuple[int, bytearray, list[bytes]]] = []

    index = 0
    while True:
        offset = layout.mft_offset + index * layout.mft_record_size
        if offset + layout.mft_record_size > len(buf):
            break
        record = bytearray(buf[offset : offset + layout.mft_record_size])
        usa: list[bytes] = []
        if record[0:4] == b"FILE":
            usa = _apply_fixup(record, sector_size)
            attrs_offset = struct.unpack_from("<H", record, 0x14)[0]
            name = ""
            si_offset = fn_offset = None
            for attr_offset, attr_type, _length in _iter_attributes(record, attrs_offset):
                if attr_type == ATTR_SI:
                    si_offset = attr_offset
                elif attr_type == ATTR_FN:
                    fn_offset = attr_offset
                    name, _namespace = _fn_name(record, attr_offset)
            key = name.lower() if name else ""
            if si_offset is not None and fn_offset is not None and key in entries:
                _patch_times(record, si_offset, entries[key]["si"])
                _patch_times(record, fn_offset, entries[key]["fn"], value_skip=8)
                matched[name] = _read_times(record, si_offset) + _read_times(record, fn_offset, value_skip=8)
            elif si_offset is not None:
                _patch_times(record, si_offset, base_ft)
                if fn_offset is not None:
                    _patch_times(record, fn_offset, base_ft, value_skip=8)
            for attr_offset, attr_type, _length in _iter_attributes(record, attrs_offset):
                if attr_type == ATTR_INDEX_ROOT:
                    _patch_index_root(record, attr_offset, horizon_ft, base_ft, sector_size)
                elif attr_type == ATTR_DATA and index == 2:  # $LogFile
                    _zero_nonresident_runs(buf, record, attr_offset, layout)
            if name == "$UsnJrnl":
                for attr_offset, attr_type, _length in _iter_attributes(record, attrs_offset):
                    if attr_type == ATTR_DATA and _read_attr_name(record, attr_offset) == "$J":
                        _zero_nonresident_runs(buf, record, attr_offset, layout)
            _restore_fixup(record, usa, sector_size)
        mft_records.append((offset, record, usa))
        index += 1

    for offset, record, _usa in mft_records:
        buf[offset : offset + layout.mft_record_size] = record

    # $INDEX_ALLOCATION buffers (INDX): non-resident directory indexes carry
    # wall-clock FILE_NAME timestamps (mkntfs metafile set spills the root
    # index). Normalized to base time like the records above.
    _patch_indx_buffers(buf, layout, horizon_ft, base_ft)

    # $MFTMirr: mirror the first records of the patched $MFT.
    mirr_offset = layout.cluster_offset(layout.mftmirr_lcn)
    for i in range(4):
        src = layout.mft_offset + i * layout.mft_record_size
        buf[mirr_offset + i * layout.mft_record_size : mirr_offset + (i + 1) * layout.mft_record_size] = buf[src : src + layout.mft_record_size]

    # Boot serial (primary + backup copy at image end).
    serial_bytes = struct.pack("<Q", serial)
    buf[0x48:0x50] = serial_bytes
    buf[-0x200 + 0x48 : -0x200 + 0x50] = serial_bytes

    Path(image_path).write_bytes(buf)
    return matched


def read_entries(image_path: Path, names: list[str]) -> dict[str, list[int]]:
    """Read SI+FN timestamps of the given basenames (test verification)."""
    buf = Path(image_path).read_bytes()
    layout = _MftLayout(buf)
    sector_size = layout.bytes_per_sector
    wanted = {name.lower() for name in names}
    found: dict[str, list[int]] = {}
    index = 0
    while layout.mft_offset + (index + 1) * layout.mft_record_size <= len(buf):
        offset = layout.mft_offset + index * layout.mft_record_size
        record = bytearray(buf[offset : offset + layout.mft_record_size])
        if record[0:4] != b"FILE":
            break
        _apply_fixup(record, sector_size)
        attrs_offset = struct.unpack_from("<H", record, 0x14)[0]
        si_offset = fn_offset = None
        name = ""
        for attr_offset, attr_type, _length in _iter_attributes(record, attrs_offset):
            if attr_type == ATTR_SI:
                si_offset = attr_offset
            elif attr_type == ATTR_FN:
                fn_offset = attr_offset
                name, _ns = _fn_name(record, attr_offset)
        if name.lower() in wanted and si_offset is not None and fn_offset is not None:
            found[name] = _read_times(record, si_offset) + _read_times(record, fn_offset, value_skip=8)
        index += 1
    return found


def boot_serial(image_path: Path) -> int:
    buf = Path(image_path).read_bytes()
    return struct.unpack_from("<Q", buf, 0x48)[0]
