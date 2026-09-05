"""oreoa CLI - thin commands the runtime slash commands call (spec, Tech stack).

Subcommands (step 1 scope):
  case new <id> --type incident|exercice [--name] [--analyst]   scaffold + switch
  case list                                                     cases on disk
  case switch <id>                                              point .current at it
  case current                                                  print current id
  banner                                                        persistent banner line
  runtime-config render [--out DIR]                             render runtime config

Paths resolve from OREOA_CASES (container: /cases; host: ./cases).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def cases_root() -> Path:
    return Path(os.environ.get("OREOA_CASES", "cases")).resolve()


def current_case_file(root: Path) -> Path:
    return root / ".current"


def read_current(root: Path) -> str:
    f = current_case_file(root)
    if f.is_file():
        value = f.read_text(encoding="utf-8").strip()
        if value:
            return value
    return ""


def write_current(root: Path, case_id: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    current_case_file(root).write_text(case_id + "\n", encoding="utf-8")


def cmd_case_new(args: argparse.Namespace) -> int:
    from .scaffold import scaffold_case

    root = cases_root()
    try:
        case_dir = scaffold_case(
            root,
            args.id,
            args.type,
            name=args.name,
            analyst=args.analyst or os.environ.get("OREOA_ANALYST", ""),
            model=os.environ.get("LLM_MODEL_ANALYST", ""),
        )
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_current(root, args.id)
    kind = "EXERCICE" if args.type == "exercice" else "INCIDENT"
    print(f"case created: {case_dir} ({kind}) - now the current case")
    if args.type == "exercice":
        print("answers.yaml created (score layer only, never mounted into MCP servers)")
    return 0


def cmd_case_list(args: argparse.Namespace) -> int:
    import yaml

    root = cases_root()
    if not root.is_dir():
        print("no cases yet (oreoa case new <id>)")
        return 0
    current = read_current(root)
    rows = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        case_yaml = d / "case.yaml"
        ctype, status = "?", "?"
        if case_yaml.is_file():
            try:
                meta = yaml.safe_load(case_yaml.read_text(encoding="utf-8")) or {}
                c = meta.get("case", {})
                ctype, status = c.get("type", "?"), c.get("status", "?")
            except Exception:
                pass
        marker = "*" if d.name == current else " "
        rows.append(f"{marker} {d.name:24s} {ctype:9s} {status}")
    if not rows:
        print("no cases yet (oreoa case new <id>)")
        return 0
    print("id                       type      status   (* = current)")
    for r in rows:
        print(r)
    return 0


def cmd_case_switch(args: argparse.Namespace) -> int:
    from .case_model import load_case

    root = cases_root()
    case_dir = root / args.id
    if not (case_dir / "case.yaml").is_file():
        print(f"error: no case at {case_dir}", file=sys.stderr)
        return 1
    try:
        cf = load_case(case_dir / "case.yaml")
    except Exception as exc:
        print(f"error: case.yaml invalid: {exc}", file=sys.stderr)
        return 1
    write_current(root, cf.case.id)
    print(f"current case: {cf.case.id} ({cf.case.type})")
    return 0


def cmd_case_current(args: argparse.Namespace) -> int:
    current = read_current(cases_root())
    print(current if current else "(none)")
    return 0


def cmd_banner(args: argparse.Namespace) -> int:
    root = cases_root()
    case_id = read_current(root)
    if not case_id:
        print("No active case (oreoa case new <id> | oreoa case switch <id>)")
        return 1
    case_type = "?"
    case_yaml = root / case_id / "case.yaml"
    if case_yaml.is_file():
        import yaml

        meta = yaml.safe_load(case_yaml.read_text(encoding="utf-8")) or {}
        case_type = (meta.get("case", {}) or {}).get("type", "?")
    model = os.environ.get("LLM_MODEL_ANALYST", "").strip() or "unset"
    endpoint = os.environ.get("LLM_BASE_URL", "").strip() or "unset"
    print(f"Case: {case_id} · {case_type.upper()} · Model: {model} @ {endpoint}")
    return 0


def cmd_runtime_config(args: argparse.Namespace) -> int:
    from .runtime_config import render

    out = Path(args.out).resolve() if args.out else Path(os.environ.get("OREOA_ROOT", Path.cwd()))
    runtimes: tuple[str, ...] = tuple(args.runtimes.split(",")) if args.runtimes else ("opencode", "claude")
    layout = args.layout or "project"
    written = render(out, runtimes=runtimes, layout=layout)
    for p in written:
        print(f"rendered {p}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oreoa", description="OREOA-AI platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    case = sub.add_parser("case", help="case management")
    case_sub = case.add_subparsers(dest="case_command", required=True)

    new = case_sub.add_parser("new", help="create a case skeleton and make it current")
    new.add_argument("id", help="case id (directory name)")
    new.add_argument("--type", choices=["incident", "exercice"], default="incident")
    new.add_argument("--name", default="")
    new.add_argument("--analyst", default="")
    new.set_defaults(func=cmd_case_new)

    lst = case_sub.add_parser("list", help="list cases")
    lst.set_defaults(func=cmd_case_list)

    switch = case_sub.add_parser("switch", help="make an existing case current")
    switch.add_argument("id")
    switch.set_defaults(func=cmd_case_switch)

    cur = case_sub.add_parser("current", help="print the current case id")
    cur.set_defaults(func=cmd_case_current)

    banner = sub.add_parser("banner", help="print the persistent analyst banner")
    banner.set_defaults(func=cmd_banner)

    rc = sub.add_parser("runtime-config", help="runtime config generator")
    rc_sub = rc.add_subparsers(dest="rc_command", required=True)
    rcr = rc_sub.add_parser("render", help="render opencode + claude-code config")
    rcr.add_argument("--out", default="", help="output root (default: cwd or OREOA_ROOT)")
    rcr.add_argument("--runtimes", default="", help="comma list: opencode,claude (default: both)")
    rcr.add_argument("--layout", default="", help="project | global (default: project)")
    rcr.set_defaults(func=cmd_runtime_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def console_entry() -> None:
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
