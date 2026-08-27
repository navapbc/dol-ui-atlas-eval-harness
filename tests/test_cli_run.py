import csv
from pathlib import Path

import pytest

from atlas_eval.cli import main
from atlas_eval.runs import read_run

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the ACP.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
"""

# A bank crafted so that "any column holding True" and "deterministic_pass is
# True" disagree for one question: v3-Q2's answer satisfies required_all (so
# required_all_pass and required_any_pass are both True) but also contains
# the forbidden term, so forbidden_pass is False and deterministic_pass is
# False overall. A scores.csv line for that row still contains the literal
# substring ",True," (from the two adjacent True columns), which is exactly
# what the old buggy count keyed on.
PASS_COUNT_TRAP_BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the ACP.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
  - id: v3-Q2
    text: Describe the ACP without naming the banned term.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
      forbidden: [banned-term]
  - id: v3-Q3
    text: Describe the ACP again.
    type: retrieval
    expected_stance: answer
    ground_truth: ACP is the Accelerated Collection Process.
    checks:
      required_all: [ACP]
"""


def _bank(tmp_path):
    p = tmp_path / "v3.yaml"
    p.write_text(BANK)
    return p


def test_paste_transport_end_to_end(tmp_path, capsys):
    bank = _bank(tmp_path)
    transcript = tmp_path / "pasted.md"
    transcript.write_text(
        "<!-- atlas:answer v3-Q1 -->\nThe ACP is the Accelerated Collection Process.\n"
    )
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "complete" in out

    run_dir = next(runs.iterdir())
    meta, responses, rows = read_run(run_dir)
    assert meta.transport == "paste"
    assert responses["v3-Q1"].startswith("The ACP")
    assert len(rows) == 1


def test_paste_transport_requires_a_transcript(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--transcript" in capsys.readouterr().out


def test_incomplete_paste_exits_nonzero_but_still_writes_the_run(tmp_path, capsys):
    bank = tmp_path / "v3.yaml"
    bank.write_text(BANK + """  - id: v3-Q2
    text: And what does ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
""")
    transcript = tmp_path / "pasted.md"
    transcript.write_text("<!-- atlas:answer v3-Q1 -->\nThe ACP.\n")
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 1, "an incomplete run must not report success"
    assert "incomplete" in capsys.readouterr().out.lower()
    assert read_run(next(runs.iterdir()))[0].status.value == "incomplete"


def test_print_sheet_emits_the_run_sheet_and_exits_zero(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--print-sheet", "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out
    assert "v3-Q1" in out
    assert "<!-- atlas:answer v3-Q1 -->" in out
    assert "Describe the ACP." in out
    assert "same conversation" in out.lower()


class _FakePersistentContext:
    """Stands in for a Playwright BrowserContext: tracks whether it was closed."""

    def __init__(self, page) -> None:
        self.pages = [page]
        self.closed = False

    def new_page(self):
        raise AssertionError("pages was pre-seeded; new_page should not be called")

    def close(self) -> None:
        self.closed = True


class _FakeFailingPage:
    """A page whose .goto raises, simulating a bad URL or navigation timeout."""

    def goto(self, url):
        raise RuntimeError("navigation boom")


class _FakeChromium:
    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def launch_persistent_context(self, *args, **kwargs):
        return self._ctx


class _FakePlaywright:
    def __init__(self, ctx) -> None:
        self.chromium = _FakeChromium(ctx)


class _FakeSyncPlaywrightCM:
    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def __enter__(self):
        return _FakePlaywright(self._ctx)

    def __exit__(self, exc_type, exc, tb):
        return False


def test_context_is_closed_when_goto_fails_before_the_run_starts(tmp_path, monkeypatch):
    """A bad URL or nav error between opening the context and starting the run

    must not leak a headed, signed-in browser: ctx.close() must still run.
    """
    ctx = _FakePersistentContext(_FakeFailingPage())
    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright", lambda: _FakeSyncPlaywrightCM(ctx)
    )

    profile = tmp_path / "profile"
    profile.mkdir()

    with pytest.raises(RuntimeError, match="navigation boom"):
        main(["run", "--bank", str(_bank(tmp_path)), "--transport", "playwright",
              "--url", "https://example.com/agent", "--profile-dir", str(profile),
              "--runs", str(tmp_path / "runs"), "--no-snapshot"])

    assert ctx.closed, "the context must be closed even when goto raises before the run"


class _OkPage:
    """A page whose .goto succeeds, so the flow can reach run_bank if the
    hash check doesn't stop it first."""

    def goto(self, url):
        pass


def test_playwright_transport_refuses_a_frozen_hash_mismatch_before_opening_a_browser(
    tmp_path, monkeypatch,
):
    """The bank's frozen-hash check must run before any browser is opened or
    any live URL is hit -- a doomed run (question_sha256 mismatch) must not
    pay the cost, or the risk, of a headed browser session first.
    """
    from atlas_eval.dataset import compute_question_sha256, load_bank

    bank_path = tmp_path / "v3.yaml"
    bank_path.write_text(BANK)
    digest = compute_question_sha256(load_bank(bank_path))
    bank_path.write_text(
        BANK.replace("version: v3",
                     f"version: v3\nfrozen_on: 2026-08-03\nquestion_sha256: {digest}")
    )
    # Edit the question text after freezing, so the recorded hash no longer matches.
    bank_path.write_text(bank_path.read_text().replace("Describe the ACP.",
                                                        "Describe the ACP now."))

    opened = {"n": 0}

    class _CountingChromium:
        def launch_persistent_context(self, *args, **kwargs):
            opened["n"] += 1
            return _FakePersistentContext(_OkPage())

    class _CountingPlaywright:
        chromium = _CountingChromium()

    class _CountingCM:
        def __enter__(self):
            return _CountingPlaywright()

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("playwright.sync_api.sync_playwright", lambda: _CountingCM())

    profile = tmp_path / "profile"
    profile.mkdir()

    code = main(["run", "--bank", str(bank_path), "--transport", "playwright",
                 "--url", "https://example.com/agent", "--profile-dir", str(profile),
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])

    assert code == 2
    assert opened["n"] == 0, "a doomed run must not open a browser at all"


def test_playwright_transport_requires_a_url(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "playwright",
                 "--runs", str(tmp_path / "runs"), "--no-snapshot"])
    assert code == 2
    assert "--url" in capsys.readouterr().out


def test_missing_bank_exits_two(tmp_path, capsys):
    code = main(["run", "--bank", str(tmp_path / "nope.yaml"), "--transport", "paste",
                 "--transcript", str(tmp_path / "t.md"), "--runs", str(tmp_path / "runs"),
                 "--no-snapshot"])
    assert code == 2


def test_run_help_lists_both_transports(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    out = capsys.readouterr().out
    # argparse's own "{paste,playwright}" choices listing would satisfy a bare
    # substring check regardless of whether the descriptive help text is
    # right, so assert on wording from the actual --transport and
    # --no-snapshot help strings instead.
    assert "you drive Quick and paste the transcript" in out
    assert "drive the UI (needs a signed-in profile)" in out
    assert "score cannot be interpreted later" in out


def test_print_sheet_needs_only_bank_no_aws_flags(tmp_path, capsys):
    """--print-sheet reads only the bank file; it must never demand --account-id."""
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste",
                 "--print-sheet"])
    assert code == 0
    out = capsys.readouterr().out
    assert "v3-Q1" in out
    assert "<!-- atlas:answer v3-Q1 -->" in out
    assert "Describe the ACP." in out


def test_missing_bank_exits_two_without_snapshot_flags(tmp_path, capsys):
    code = main(["run", "--bank", str(tmp_path / "nope.yaml"), "--transport", "paste"])
    assert code == 2
    out = capsys.readouterr().out
    assert "account-id" not in out.lower()


def test_missing_transcript_exits_two_without_snapshot_flags(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "paste"])
    assert code == 2
    out = capsys.readouterr().out
    assert "--transcript" in out
    assert "account-id" not in out.lower()


def test_missing_url_exits_two_without_snapshot_flags(tmp_path, capsys):
    code = main(["run", "--bank", str(_bank(tmp_path)), "--transport", "playwright"])
    assert code == 2
    out = capsys.readouterr().out
    assert "--url" in out
    assert "account-id" not in out.lower()


def test_pass_count_matches_scores_csv_deterministic_pass_column(tmp_path, capsys):
    """`run`'s printed pass count must agree with report's own deterministic_pass tally.

    v3-Q2 is a trap: its scores.csv row has other True-valued columns
    (required_all_pass, required_any_pass) even though deterministic_pass
    itself is False, so a naive ",True," substring count over-reports. The
    fixture is built so the correct pass count (2) is deliberately not equal
    to the row count (3), so an off-by-all bug cannot pass this test.
    """
    bank = tmp_path / "v3.yaml"
    bank.write_text(PASS_COUNT_TRAP_BANK)
    transcript = tmp_path / "pasted.md"
    transcript.write_text(
        "<!-- atlas:answer v3-Q1 -->\nThe ACP is the Accelerated Collection Process.\n"
        "<!-- atlas:answer v3-Q2 -->\nThe ACP is the Accelerated Collection Process, "
        "which some call the banned-term.\n"
        "<!-- atlas:answer v3-Q3 -->\nThe ACP is the Accelerated Collection Process.\n"
    )
    runs = tmp_path / "runs"

    code = main(["run", "--bank", str(bank), "--transport", "paste",
                 "--transcript", str(transcript), "--runs", str(runs), "--no-snapshot"])
    assert code == 0
    out = capsys.readouterr().out

    run_dir = next(runs.iterdir())
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        score_rows = list(csv.DictReader(fh))
    actual_passes = sum(1 for r in score_rows if r["deterministic_pass"] == "True")

    assert actual_passes != len(score_rows), "fixture must not make pass count equal row count"
    assert f"deterministic_pass: {actual_passes}/{len(score_rows)}" in out
