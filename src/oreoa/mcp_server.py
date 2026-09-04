"""MCP servers entrypoint placeholder.

Real servers (mcp-evidence, mcp-knowledge, mcp-case, mcp-jobs, streamable
HTTP on :8000, data delimiters, row caps, case-id enforcement) are implemented
at work-order step 1.4.
"""

import sys

SERVERS = ("evidence", "knowledge", "case", "jobs")


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else ""
    if name not in SERVERS:
        print(f"unknown mcp server: {name!r} (expected one of {', '.join(SERVERS)})", file=sys.stderr)
        return 2
    print(f"mcp-{name}: implemented at work-order step 1.4", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
