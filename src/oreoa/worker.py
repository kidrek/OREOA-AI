"""RQ worker harness placeholder.

Real harness (queues fast/deep, per-step job_timeout from packs, manifest and
phase writes, resource caps) is wired at work-order step 1.4.
"""

import sys


def main() -> int:
    print("oreoa worker harness: Redis/RQ wiring lands at work-order step 1.4", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
