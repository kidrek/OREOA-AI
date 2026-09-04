# RQ harness for queue `fetch` - wired at work-order step 1.5 (symbols on demand).
import sys


def main() -> int:
    print("oreoa fetcher: symbol-fetch wiring lands at step 1.5", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
