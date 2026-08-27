import csv
from datetime import datetime
from pathlib import Path

import pytest

from atlas_eval.cli import main
from atlas_eval.dataset import compute_question_sha256, load_bank
from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.rescore import RescoreError, rescore_run
from atlas_eval.runs import ROLLUP_COLUMNS, RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.scoring import Rubric, score_answer

AGENT_ID = "093ac4e3-0712-481e-af95-9ddc5e4fc734"
CONV = "e33bea76-a1f6-4c78-8c1d-9d735e3dfb82"

# The bank as it stands NOW: required_all no longer wrongly demands the bare
# acronym "ACP" (that was the bug); required_any covers the redirect names.
BANK_YAML = """\
version: v1
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v1-Q1
    text: Describe the Automated Collection Process.
    type: term_redirect
    expected_stance: redirect
    ground_truth: gt
    checks:
      required_all: []
      required_any: ["Accelerated Collection Process"]
      expect_citations: []
"""

# The question as the harness would have scored it AT RUN TIME, before the
# checks fix: required_all wrongly demanded the bare acronym.
BUGGY_QUESTION = Question(
    id="v1-Q1", text="Describe the Automated Collection Process.",
    type=QuestionType.TERM_REDIRECT, expected_stance=Stance.REDIRECT, ground_truth="gt",
    checks=Checks(required_all=["ACP"], required_any=["Accelerated Collection Process"]),
)

ANSWER = "The Accelerated Collection Process is documented in UIMB0730."


def _banks_dir(tmp_path: Path) -> Path:
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v1.yaml").write_text(BANK_YAML, encoding="utf-8")
    return banks


def _current_sha(banks: Path) -> str:
    return compute_question_sha256(load_bank(banks / "v1.yaml"))


def _meta(sha: str, **over) -> RunMeta:
    base = dict(
        run_id="2026-08-27_0900_quick_paste_v1", backend="quick", transport="paste",
        bank_version="v1", question_sha256=sha,
        agent="engineering_onboarding_specialist", agent_id=AGENT_ID,
        conversation_id=CONV,
        started_at=datetime(2026, 8, 27, 9, 0), finished_at=datetime(2026, 8, 27, 9, 0),
        harness_git_sha=None, status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _write_buggy_run(tmp_path: Path, sha: str, rubric: Rubric | None = None) -> Path:
    """A run scored under the pre-fix checks: v1-Q1 wrongly fails on 'ACP'."""
    runs = tmp_path / "runs"
    rubric = rubric if rubric is not None else Rubric(
        citations=1, correctness=2, gap_honesty=2, scope_discipline=2, clarity=2,
        notes="old note", scored_by="claude-opus-5", confirmed_by="michael",
    )
    row = ScoreRow(
        question_id="v1-Q1", type=QuestionType.TERM_REDIRECT.value,
        verification_status="unverified", rubric=rubric,
        deterministic=score_answer(BUGGY_QUESTION, ANSWER),
    )
    return write_run(runs, _meta(sha), {"v1-Q1": ANSWER}, "# transcript\n", {}, [row])


def _read_rows(run_dir: Path) -> dict[str, dict]:
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        return {r["question_id"]: r for r in csv.DictReader(fh)}


def test_check_term_fix_corrects_deterministic_columns(tmp_path):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)

    old_rows = _read_rows(run_dir)
    assert old_rows["v1-Q1"]["missing_required"] == "ACP"
    assert old_rows["v1-Q1"]["deterministic_pass"] == "False"

    result = rescore_run(run_dir, banks)

    new_rows = _read_rows(run_dir)
    assert new_rows["v1-Q1"]["missing_required"] == ""
    assert new_rows["v1-Q1"]["deterministic_pass"] == "True"
    assert result.status == "rescored"
    assert len(result.changed_diffs) == 1
    assert result.written is True


def test_rubric_columns_and_provenance_survive_byte_for_byte(tmp_path):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)
    old_rows = _read_rows(run_dir)

    rescore_run(run_dir, banks)

    new_rows = _read_rows(run_dir)
    for col in ("citations", "correctness", "gap_honesty", "scope_discipline",
                "clarity", "total", "notes", "scored_by", "confirmed_by"):
        assert new_rows["v1-Q1"][col] == old_rows["v1-Q1"][col], col


def test_bank_hash_mismatch_is_refused_and_writes_nothing(tmp_path):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)

    # The bank's question text changes after the run was scored.
    (banks / "v1.yaml").write_text(
        BANK_YAML.replace(
            "Describe the Automated Collection Process.",
            "Describe the Accelerated Collection Process end to end.",
        ),
        encoding="utf-8",
    )
    before = (run_dir / "scores.csv").read_text(encoding="utf-8")

    with pytest.raises(RescoreError):
        rescore_run(run_dir, banks)

    after = (run_dir / "scores.csv").read_text(encoding="utf-8")
    assert after == before


def test_dry_run_reports_diff_and_writes_nothing(tmp_path):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)
    before = (run_dir / "scores.csv").read_text(encoding="utf-8")

    result = rescore_run(run_dir, banks, dry_run=True)

    after = (run_dir / "scores.csv").read_text(encoding="utf-8")
    assert after == before
    assert result.status == "rescored"
    assert result.written is False
    assert len(result.changed_diffs) == 1


def test_no_changes_reports_so_and_leaves_file_byte_identical(tmp_path):
    banks = _banks_dir(tmp_path)
    bank = load_bank(banks / "v1.yaml")
    sha = compute_question_sha256(bank)
    fixed_question = bank.questions[0]  # already has the current, fixed checks

    runs = tmp_path / "runs"
    row = ScoreRow(
        question_id="v1-Q1", type=QuestionType.TERM_REDIRECT.value,
        verification_status="unverified",
        rubric=Rubric(citations=2, correctness=2, gap_honesty=2, scope_discipline=2,
                      clarity=2, scored_by="claude-opus-5", confirmed_by="michael"),
        deterministic=score_answer(fixed_question, ANSWER),
    )
    run_dir = write_run(runs, _meta(sha), {"v1-Q1": ANSWER}, "# transcript\n", {}, [row])
    before = (run_dir / "scores.csv").read_text(encoding="utf-8")

    result = rescore_run(run_dir, banks)

    after = (run_dir / "scores.csv").read_text(encoding="utf-8")
    assert after == before
    assert result.status == "unchanged"
    assert result.changed_diffs == []
    assert result.written is False


def test_legacy_unknown_hash_is_skipped_not_rescored(tmp_path):
    banks = _banks_dir(tmp_path)
    run_dir = _write_buggy_run(tmp_path, "legacy-unknown")
    before = (run_dir / "scores.csv").read_text(encoding="utf-8")

    result = rescore_run(run_dir, banks)

    after = (run_dir / "scores.csv").read_text(encoding="utf-8")
    assert after == before
    assert result.status == "skipped-legacy"
    assert result.written is False


def test_column_order_is_unchanged_after_rescore(tmp_path):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)

    rescore_run(run_dir, banks)

    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        assert tuple(reader.fieldnames) == ROLLUP_COLUMNS


# --- CLI -----------------------------------------------------------------

def test_cli_rescore_single_run_prints_diff_and_exits_zero(tmp_path, capsys):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)

    exit_code = main(["rescore", "--run", str(run_dir), "--banks", str(banks)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "v1-Q1" in out
    assert "False -> True" in out


def test_cli_rescore_hash_mismatch_exits_2_and_writes_nothing(tmp_path, capsys):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    run_dir = _write_buggy_run(tmp_path, sha)
    (banks / "v1.yaml").write_text(
        BANK_YAML.replace(
            "Describe the Automated Collection Process.",
            "Describe the Accelerated Collection Process end to end.",
        ),
        encoding="utf-8",
    )
    before = (run_dir / "scores.csv").read_text(encoding="utf-8")

    exit_code = main(["rescore", "--run", str(run_dir), "--banks", str(banks)])

    assert exit_code == 2
    assert "error" in capsys.readouterr().out.lower()
    assert (run_dir / "scores.csv").read_text(encoding="utf-8") == before


def test_cli_rescore_runs_dir_processes_every_run(tmp_path, capsys):
    banks = _banks_dir(tmp_path)
    sha = _current_sha(banks)
    runs = tmp_path / "runs"
    _write_buggy_run(tmp_path, sha)  # writes into tmp_path/runs already
    exit_code = main(["rescore", "--runs", str(runs), "--banks", str(banks)])

    assert exit_code == 0
    assert "v1-Q1" in capsys.readouterr().out
