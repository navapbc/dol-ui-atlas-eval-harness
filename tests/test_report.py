from datetime import date, datetime
from pathlib import Path

import pytest

from atlas_eval.models import (
    Bank, Checks, Question, QuestionType, Stance, Verification, VerificationStatus,
)
from atlas_eval.report import build_report, format_report
from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.scoring import Rubric, score_answer

BANK = """version: v3
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: verified question
    type: retrieval
    expected_stance: answer
    ground_truth: gt
    checks:
      required_all: [ACP]
    verification:
      status: verified
      verified_by: Oscar
      verified_on: 2026-08-28
  - id: v3-Q2
    text: unverified question
    type: retrieval
    expected_stance: answer
    ground_truth: gt
    checks:
      required_all: [DXCBDA2R]
    verification:
      status: unverified
"""


def _setup(tmp_path, q1_answer, q2_answer, confirmed=True):
    banks = tmp_path / "banks"
    banks.mkdir(parents=True)
    (banks / "v3.yaml").write_text(BANK)

    from atlas_eval.dataset import load_bank
    bank = load_bank(banks / "v3.yaml")
    q1, q2 = bank.questions

    def row(q, answer):
        return ScoreRow(
            question_id=q.id, type=q.type.value,
            verification_status=q.verification.status.value,
            rubric=Rubric(citations=2, correctness=2, gap_honesty=2,
                          scope_discipline=2, clarity=2,
                          scored_by="claude-opus-5",
                          confirmed_by="Michael" if confirmed else None),
            deterministic=score_answer(q, answer),
        )

    meta = RunMeta(
        run_id="2026-08-28_1000_quick_v3", backend="quick", transport="paste",
        bank_version="v3", question_sha256="x" * 64, agent="a",
        started_at=datetime(2026, 8, 28, 10, 0), finished_at=datetime(2026, 8, 28, 10, 30),
        status=RunStatus.COMPLETE,
    )
    runs = tmp_path / "runs"
    run_dir = write_run(runs, meta, {q1.id: q1_answer, q2.id: q2_answer}, "t", {},
                        [row(q1, q1_answer), row(q2, q2_answer)])
    return run_dir, banks


def test_verified_and_exploratory_counts_differ(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert rep.verified.question_count == 1
    assert rep.exploratory.question_count == 2
    assert rep.verified.label == "verified"
    assert rep.exploratory.label == "exploratory (unvetted)"


def test_verified_subset_excludes_unverified_failures(tmp_path):
    # Q1 (verified) passes; Q2 (unverified) fails. The defensible number is 1/1.
    run_dir, banks = _setup(tmp_path, "the ACP applies", "no mention of the program")
    rep = build_report(run_dir, banks)
    assert (rep.verified.deterministic_pass, rep.verified.question_count) == (1, 1)
    assert (rep.exploratory.deterministic_pass, rep.exploratory.question_count) == (1, 2)


def test_rubric_totals_are_summed_over_each_subset(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert (rep.verified.rubric_total, rep.verified.rubric_max) == (10, 10)
    assert (rep.exploratory.rubric_total, rep.exploratory.rubric_max) == (20, 20)


def test_confirmed_count_tracks_human_signoff(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "DXCBDA2R runs nightly",
                            confirmed=False)
    rep = build_report(run_dir, banks)
    assert rep.exploratory.confirmed_count == 0
    assert rep.verified.confirmed_count == 0


def test_report_refuses_an_incomplete_run(tmp_path):
    run_dir, banks = _setup(tmp_path, "a", "b")
    text = (run_dir / "run.yaml").read_text().replace("complete", "incomplete")
    (run_dir / "run.yaml").write_text(text)
    with pytest.raises(ValueError) as exc:
        build_report(run_dir, banks)
    assert "incomplete" in str(exc.value)


def test_format_labels_the_unvetted_figure_explicitly(tmp_path):
    run_dir, banks = _setup(tmp_path, "the ACP applies", "no mention")
    text = format_report(build_report(run_dir, banks))
    assert "verified" in text and "unvetted" in text
    assert "1/1" in text and "1/2" in text
    # The two figures must never be presented as one number.
    assert "combined" not in text.lower()


def test_format_warns_when_no_questions_are_verified(tmp_path):
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v3.yaml").write_text(BANK.replace("status: verified", "status: unverified")
                                       .replace("verified_by: Oscar", "verified_by: null")
                                       .replace("verified_on: 2026-08-28", "verified_on: null"))
    run_dir, _ = _setup(tmp_path / "other", "the ACP applies", "DXCBDA2R runs nightly")
    rep = build_report(run_dir, banks)
    assert rep.verified.question_count == 0
    text = format_report(rep)
    assert "no verified questions" in text.lower()
