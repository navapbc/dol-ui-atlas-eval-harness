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


def _cmd_rollup(args: argparse.Namespace) -> int:
    import difflib
    import tempfile

    from atlas_eval.runs import regenerate_rollup

    runs_dir = Path(args.runs)
    out_path = Path(args.out)

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh_path = Path(tmp) / out_path.name
            regenerate_rollup(runs_dir, fresh_path)
            fresh = fresh_path.read_text(encoding="utf-8")
        current = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if fresh == current:
            print(f"{out_path} is up to date with {runs_dir}.")
            return 0
        print(f"{out_path} is out of date with {runs_dir}; it would change:\n")
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            fresh.splitlines(keepends=True),
            fromfile=str(out_path),
            tofile="regenerated",
        )
        print("".join(diff))
        print(f"\nrun `atlas-eval rollup --runs {runs_dir} --out {out_path}` "
              "and commit the result.")
        return 1

    n = regenerate_rollup(runs_dir, out_path)
    print(f"regenerated {out_path} from {n} complete run(s)")
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


def _cmd_run(args: argparse.Namespace) -> int:
    from atlas_eval.adapters.quick_paste import QuickPasteBackend
    from atlas_eval.orchestrate import OrchestrationError, run_bank

    # Validation order, cheapest and most-local first: a user fixing a typo'd
    # flag should never be told to go authenticate with AWS first.
    #   1. does the bank file exist (needed by every path, including
    #      --print-sheet, which reads only this)
    #   2. --print-sheet: satisfied by the bank alone, so handle and exit
    #      before anything else is asked for
    #   3. the other transport-specific, purely-local requirements
    #      (--transcript/its file, --url/its browser profile)
    #   4. only once all of the above hold: the control-plane snapshot, the
    #      one step that actually talks to AWS
    bank_path = Path(args.bank)
    if not bank_path.is_file():
        print(f"error: no such bank file: {bank_path}")
        return 2

    if args.print_sheet and args.transport != "paste":
        # --print-sheet only means anything for the paste transport (no AWS,
        # no URL, no browser needed): under playwright it was silently
        # ignored rather than flagged as the operator's mistake.
        print(f"error: --print-sheet is only meaningful with --transport paste, "
              f"not --transport {args.transport}")
        return 2

    if args.transport == "paste" and args.print_sheet:
        from atlas_eval.adapters.quick_paste import render_prompt_sheet
        from atlas_eval.dataset import load_bank, resolve_run_order
        print(render_prompt_sheet(resolve_run_order(load_bank(bank_path))))
        return 0

    transcript_path: Path | None = None
    profile: Path | None = None
    if args.transport == "paste":
        if not args.transcript:
            print("error: --transcript is required for the paste transport "
                  "(or pass --print-sheet to generate the sheet to fill in)")
            return 2
        transcript_path = Path(args.transcript)
        if not transcript_path.is_file():
            print(f"error: no such transcript: {transcript_path}")
            return 2
    else:
        if not args.url:
            print("error: --url is required for the playwright transport")
            return 2
        profile = Path(args.profile_dir)
        if not profile.exists():
            print(f"error: no browser profile at {profile}. Run "
                  f"tools/open_quick_session.py first and sign in once.")
            return 2

    snapshot_data: dict = {}
    if not args.no_snapshot:
        from atlas_eval.snapshot import SnapshotError, capture
        if not args.account_id:
            print("error: --account-id is required unless --no-snapshot is given")
            return 2
        try:
            snapshot_data = capture(args.account_id, agent_id=args.agent_id,
                                    agent_name=args.agent_name,
                                    profile=args.profile)
        except SnapshotError as err:
            print(f"error: snapshot failed: {err}")
            return 2

    if args.transport == "paste":
        backend = QuickPasteBackend(agent=args.agent_name or "",
                                    snapshot_data=snapshot_data,
                                    transcript_text=transcript_path.read_text(encoding="utf-8"))
        try:
            run_dir = run_bank(bank_path, backend, Path(args.runs))
        except OrchestrationError as err:
            print(f"error: {err}")
            return 2
        return _report_run(run_dir)

    from atlas_eval.orchestrate import load_and_check_bank

    # Load and hash-check the bank before opening anything: a doomed run
    # (frozen bank, changed questions) must not pay for a headed browser and
    # a live URL first. run_bank() repeats this same check internally so
    # every caller is protected, not just this one that remembered to check
    # early -- see load_and_check_bank's docstring.
    try:
        load_and_check_bank(bank_path)
    except OrchestrationError as err:
        print(f"error: {err}")
        return 2

    from playwright.sync_api import sync_playwright

    from atlas_eval.adapters.quick_playwright import QuickPlaywrightBackend
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(profile), headless=False)
        # Everything from here on can raise (a bad URL, a navigation timeout,
        # a Playwright error, an OrchestrationError from the run itself), and
        # all of it must still close the headed, signed-in context. Only the
        # context's own construction sits outside this try.
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(args.url)
            backend = QuickPlaywrightBackend(
                agent=args.agent_name or "", url=args.url,
                snapshot_data=snapshot_data, profile_dir=profile, page=page,
            )
            run_dir = run_bank(bank_path, backend, Path(args.runs))
        except OrchestrationError as err:
            print(f"error: {err}")
            return 2
        finally:
            ctx.close()
        return _report_run(run_dir)


def _report_run(run_dir: Path) -> int:
    from atlas_eval.report import read_deterministic_pass
    from atlas_eval.runs import read_run

    meta, responses, rows = read_run(run_dir)
    # Reuse report.py's own scores.csv parsing rather than re-deriving a count
    # here: a second hand-rolled tally is exactly how this drifted from what
    # `atlas-eval report` prints in the first place (a ",True," substring
    # search used to match required_all_pass/forbidden_pass/etc. too, not
    # just deterministic_pass). `run` stays self-contained -- it does not
    # call build_report/format_report, since those deliberately refuse to
    # summarise an incomplete run, and `run` must still print something
    # useful for one.
    deterministic = read_deterministic_pass(run_dir)
    passed = sum(1 for v in deterministic.values() if v is True)
    scored = sum(1 for v in deterministic.values() if v is not None)
    print(f"{meta.run_id}: {meta.status.value}")
    print(f"  answers: {len(responses)}   scored rows: {len(rows)}   "
          f"deterministic_pass: {passed}/{scored}")
    print(f"  written to {run_dir}")
    if meta.status.value != "complete":
        print("  this run is incomplete and is excluded from bank-level results")
        return 1
    return 0


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

    p_rollup = sub.add_parser("rollup", help="regenerate data/scores.csv from data/runs")
    p_rollup.add_argument("--runs", default="data/runs")
    p_rollup.add_argument("--out", default="data/scores.csv")
    p_rollup.add_argument(
        "--check", action="store_true",
        help="regenerate in memory and fail if the committed file would differ",
    )
    p_rollup.set_defaults(func=_cmd_rollup)

    p_rep = sub.add_parser("report", help="verified and exploratory scores per run")
    p_rep.add_argument("--run", help="a single run directory; default is all runs")
    p_rep.add_argument("--runs", default="data/runs")
    p_rep.add_argument("--banks", default=str(DEFAULT_BANKS))
    p_rep.set_defaults(func=_cmd_report)

    p_run = sub.add_parser("run", help="execute a bank against a backend")
    p_run.add_argument("--bank", required=True)
    p_run.add_argument("--transport", choices=("paste", "playwright"), default="paste",
                       help="paste: you drive Quick and paste the transcript. "
                            "playwright: drive the UI (needs a signed-in profile).")
    p_run.add_argument("--runs", default="data/runs")
    p_run.add_argument("--transcript", help="pasted transcript (paste transport)")
    p_run.add_argument("--print-sheet", action="store_true",
                       help="print the run sheet to fill in, then exit (paste transport)")
    p_run.add_argument("--url", help="Quick chat URL (playwright transport)")
    p_run.add_argument("--profile-dir", default=".auth/quick-profile")
    p_run.add_argument("--account-id", help="AWS account id, for the config snapshot")
    p_run.add_argument("--profile", help="named AWS CLI profile for the config snapshot")
    p_run.add_argument("--agent-id")
    p_run.add_argument("--agent-name")
    p_run.add_argument("--no-snapshot", action="store_true",
                       help="skip the control-plane snapshot, for offline testing only: "
                            "the run's agent and space configuration will not be "
                            "recorded, so its score cannot be interpreted later")
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
