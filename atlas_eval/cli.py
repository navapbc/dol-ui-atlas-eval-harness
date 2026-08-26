"""Command line entry point for the harness."""

from __future__ import annotations

import argparse
from datetime import date as _date
from pathlib import Path

from ruamel.yaml import YAML

from atlas_eval.dataset import compute_question_sha256, load_all_banks, load_bank
from atlas_eval.validation import validate_bank, validate_dir

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


def _cmd_freeze(args: argparse.Namespace) -> int:
    """Stamp frozen_on and question_sha256 in place, preserving formatting."""
    path = Path(args.bank)
    bank = load_bank(path)

    if bank.frozen_on is not None and not args.force:
        print(
            f"error: {path.name} is already frozen (frozen_on: {bank.frozen_on}).\n"
            "Editing a frozen question's text and re-freezing rewrites the hash "
            "without changing history: historical scores still point at the old "
            "question, and once the hash moves they silently point at nothing. "
            "Bank content that changes after freezing belongs in a new bank "
            "version, not a rewritten hash.\n"
            "Pass --force only if you are certain no historical score depends on "
            "this bank's current text."
        )
        return 1

    issues = validate_bank(bank, path.name)
    # A hash mismatch is expected here: that is what we are about to rewrite.
    blocking = [i for i in issues if i.code != "FROZEN_HASH_MISMATCH"]
    if blocking:
        for i in blocking:
            where = f"{i.bank}:{i.question_id}" if i.question_id else i.bank
            print(f"{where}: {i.code}: {i.message}")
        print("\nrefusing to freeze a bank with validation issues.")
        return 1

    frozen = _date.fromisoformat(args.date)
    bank.frozen_on = frozen
    digest = compute_question_sha256(bank)

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100
    with path.open(encoding="utf-8") as fh:
        doc = yaml.load(fh)
    doc["frozen_on"] = args.date
    doc["question_sha256"] = digest
    with path.open("w", encoding="utf-8") as fh:
        yaml.dump(doc, fh)

    print(f"froze {bank.version} on {args.date}: {digest[:12]} "
          f"({len(bank.questions)} questions)")
    return 0


def _cmd_review_export(args: argparse.Namespace) -> int:
    from atlas_eval.models import VerificationStatus
    from atlas_eval.review import export_review

    banks = load_all_banks(Path(args.banks))
    if args.bank:
        banks = [b for b in banks if b.version == args.bank]
        if not banks:
            print(f"error: no bank named {args.bank}")
            return 2

    statuses = None
    if args.status:
        try:
            statuses = {VerificationStatus(s) for s in args.status}
        except ValueError as err:
            print(f"error: {err}")
            return 2

    n = export_review(banks, Path(args.out), statuses)
    print(f"exported {n} question(s) to {args.out}")
    return 0


def _cmd_review_import(args: argparse.Namespace) -> int:
    from atlas_eval.review import import_review

    reviewed_on = _date.fromisoformat(args.date) if args.date else _date.today()
    report = import_review(Path(args.file), Path(args.banks), reviewed_on, args.dry_run)

    if not report.ok:
        for err in report.errors:
            print(f"error: {err}")
        print(f"\nnothing was written ({len(report.errors)} error(s)).")
        return 1

    for t in sorted(report.transitions, key=lambda t: t.question_id):
        print(f"{t.question_id}: {t.old_status.value} -> {t.new_status.value} "
              f"(by {t.reviewer})")
    verb = "would apply" if args.dry_run else "applied"
    print(f"\n{verb} {len(report.transitions)} verdict(s); "
          f"{report.unchanged} row(s) unchanged.")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    from atlas_eval.report import BankNotFoundError, IncompleteRunError, build_report, format_report

    run_dirs = (
        [Path(args.run)] if args.run
        else sorted(p for p in Path(args.runs).glob("*") if p.is_dir())
    )
    shown = 0
    had_error = False
    for run_dir in run_dirs:
        try:
            print(format_report(build_report(run_dir, Path(args.banks))))
            shown += 1
        except BankNotFoundError as err:
            # A missing or renamed bank is a configuration bug, not a routine
            # skip: it must not blend in among ordinary incomplete-run lines.
            print(f"{run_dir.name}: ERROR: {err}")
            had_error = True
        except IncompleteRunError as err:
            print(f"{run_dir.name}: skipped: {err}")
    if not shown and not had_error:
        print("no complete runs to report")
        return 1
    return 1 if had_error else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-eval")
    sub = parser.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="check every bank offline")
    p_val.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_val.set_defaults(func=_cmd_validate)

    p_freeze = sub.add_parser("freeze", help="stamp frozen_on and question_sha256")
    p_freeze.add_argument("--bank", required=True)
    p_freeze.add_argument("--date", required=True, help="freeze date, YYYY-MM-DD")
    p_freeze.add_argument(
        "--force", action="store_true",
        help="re-freeze a bank that is already frozen, rewriting its hash",
    )
    p_freeze.set_defaults(func=_cmd_freeze)

    p_review = sub.add_parser("review", help="SME review round trip")
    review_sub = p_review.add_subparsers(dest="review_command", required=True)

    p_exp = review_sub.add_parser("export", help="write the review workbook")
    p_exp.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_exp.add_argument("--bank", help="limit to one bank version, e.g. v3")
    p_exp.add_argument("--status", nargs="*",
                       help="filter by verification status, e.g. unverified needs-sme")
    p_exp.add_argument("-o", "--out", required=True)
    p_exp.set_defaults(func=_cmd_review_export)

    p_imp = review_sub.add_parser("import", help="write reviewer verdicts back")
    p_imp.add_argument("file")
    p_imp.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_imp.add_argument("--date", help="review date, YYYY-MM-DD; defaults to today")
    p_imp.add_argument("--dry-run", action="store_true")
    p_imp.set_defaults(func=_cmd_review_import)

    p_rep = sub.add_parser("report", help="verified and exploratory scores per run")
    p_rep.add_argument("--run", help="a single run directory; default is all runs")
    p_rep.add_argument("--runs", default="data/runs")
    p_rep.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_rep.set_defaults(func=_cmd_report)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
