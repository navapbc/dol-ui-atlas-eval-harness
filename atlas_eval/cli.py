"""Command line entry point for the harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from atlas_eval.dataset import load_all_banks
from atlas_eval.validation import validate_dir

DEFAULT_BANKS = Path("data/banks")


def _cmd_validate(args: argparse.Namespace) -> int:
    banks_dir = Path(args.banks)
    if not banks_dir.is_dir():
        print(f"error: no such directory: {banks_dir}")
        return 2

    issues = validate_dir(banks_dir)
    if issues:
        for i in sorted(issues, key=lambda i: (i.bank, i.question_id or "", i.code)):
            where = f"{i.bank}:{i.question_id}" if i.question_id else i.bank
            print(f"{where}: {i.code}: {i.message}")
        print(f"\n{len(issues)} issue(s) found.")
        return 1

    banks = load_all_banks(banks_dir)
    total = sum(len(b.questions) for b in banks)
    verified = sum(
        1 for b in banks for q in b.questions if q.verification.status.value == "verified"
    )
    print(f"OK: {len(banks)} bank(s), {total} question(s), {verified} verified.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-eval")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="check every bank offline")
    p_val.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_val.set_defaults(func=_cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
