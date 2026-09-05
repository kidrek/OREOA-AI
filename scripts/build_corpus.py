"""Build the T0 synthetic corpus (work-order step 1.6, ``make corpus``).

Usage: python3 scripts/build_corpus.py [--no-image] [--ntfs-image <ref>]

- ``--no-image``   build archives only (fast tests, hosts without Docker)
- ``--ntfs-image`` one-shot ntfs-3g image (default ``oreoa/corpus-ntfs:dev``,
  built by ``make corpus-image``)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oreoa.corpus_gen.builder import build_corpus  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build the OREOA-AI T0 corpus")
    parser.add_argument("--no-image", action="store_true", help="skip the raw NTFS disk images")
    parser.add_argument("--ntfs-image", default="oreoa/corpus-ntfs:dev", help="one-shot ntfs-3g image")
    args = parser.parse_args(argv)

    manifest = build_corpus(
        ROOT / "corpus",
        build_image=not args.no_image,
        ntfs_image=args.ntfs_image,
    )
    print(f"corpus built: {manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
