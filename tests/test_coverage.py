from pathlib import Path

from atlas_eval.coverage import build_coverage, format_coverage
from atlas_eval.models import VerificationStatus

BANK_A = """version: v1
frozen_on: 2026-07-27
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v1-Q1
    text: What is the ACP?
    type: retrieval
    expected_stance: answer
    ground_truth: Accelerated Collection Process.
    verification:
      status: verified
      verified_by: Oscar R.
      verified_on: 2026-08-28
  - id: v1-Q2
    text: What is the ETA-227?
    type: retrieval
    expected_stance: answer
    ground_truth: A federal refund report.
    verification:
      status: rejected
      verified_by: oscar r.
      verified_on: 2026-08-28
      notes: The ground truth conflates two reports.
  - id: v1-Q3
    text: Which operator owns terminal 7777?
    type: retrieval
    expected_stance: answer
    ground_truth: Operator 9000.
    verification:
      status: needs-sme
      verified_by: Oscar R.
      notes: Needs a CICS owner, not a batch owner.
  - id: v1-Q4
    text: Describe the monthly ACP leg.
    type: retrieval
    expected_stance: answer
    ground_truth: L2ACPM1 through M3.
"""

# Held out: no frozen_on, and nobody has looked at it.
BANK_B = """version: v2
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v2-Q1
    text: What is a PWBR?
    type: retrieval
    expected_stance: answer
    ground_truth: Partial weekly benefit rate.
  - id: v2-Q2
    text: What is the WBR formula?
    type: retrieval
    expected_stance: answer
    ground_truth: Sixty percent of average weekly wage.
    verification:
      status: verified
      verified_by: Dana K.
      verified_on: 2026-08-28
"""


def _banks(tmp_path: Path) -> Path:
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v1.yaml").write_text(BANK_A)
    (banks / "v2.yaml").write_text(BANK_B)
    return banks


def test_counts_every_status_per_bank_and_overall(tmp_path):
    cov = build_coverage(_banks(tmp_path))

    v1, v2 = cov.banks
    assert v1.version == "v1"
    assert v1.tally[VerificationStatus.VERIFIED] == 1
    assert v1.tally[VerificationStatus.REJECTED] == 1
    assert v1.tally[VerificationStatus.NEEDS_SME] == 1
    assert v1.tally[VerificationStatus.UNVERIFIED] == 1
    assert v1.tally.total == 4

    assert v2.tally[VerificationStatus.VERIFIED] == 1
    assert v2.tally[VerificationStatus.UNVERIFIED] == 1

    assert cov.overall.total == 6
    assert cov.overall[VerificationStatus.VERIFIED] == 2


def test_untouched_bank_reports_zero_reviewed(tmp_path):
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v2.yaml").write_text(
        BANK_B.replace("status: verified", "status: unverified")
    )
    cov = build_coverage(banks)
    assert cov.overall.reviewed == 0
    assert cov.overall.reviewed_pct == 0.0


def test_reviewed_progress_differs_from_verified_progress(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    v1 = cov.banks[0].tally
    # Three of four carry a verdict, but only one can feed a score.
    assert v1.reviewed == 3
    assert round(v1.reviewed_pct) == 75
    assert round(v1.verified_pct) == 25


def test_reviewer_spellings_are_folded_into_one_row(tmp_path):
    cov = build_coverage(_banks(tmp_path))

    names = {r.name: r for r in cov.reviewers}
    assert "Oscar R." in names
    oscar = names["Oscar R."]
    assert oscar.tally.total == 3
    assert oscar.variants == ["oscar r."]
    assert names["Dana K."].tally.total == 1


def test_reviewers_are_ordered_by_verdicts_returned(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert [r.name for r in cov.reviewers] == ["Oscar R.", "Dana K."]


def test_unverified_questions_have_no_reviewer_row(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert sum(r.tally.total for r in cov.reviewers) == cov.overall.reviewed


def test_needs_sme_questions_are_listed_with_their_note(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert cov.needs_sme == [("v1-Q3", "Needs a CICS owner, not a batch owner.")]


def test_a_verdict_with_no_date_is_flagged(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert cov.undated == ["v1-Q3"]


def test_held_out_bank_shows_no_freeze_date(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert cov.banks[0].frozen_on == "2026-07-27"
    assert cov.banks[1].frozen_on == ""


def test_every_question_appears_once_in_the_detail_listing(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    ids = [q.id for q in cov.questions]
    assert ids == ["v1-Q1", "v1-Q2", "v1-Q3", "v1-Q4", "v2-Q1", "v2-Q2"]


def test_format_reports_the_verified_share_when_something_is_verified(tmp_path):
    out = format_coverage(build_coverage(_banks(tmp_path)))
    assert "2 of 6 question(s) (33%) can feed a verified score." in out
    assert "awaiting a different SME (1):" in out
    assert "v1-Q3 -- Needs a CICS owner, not a batch owner." in out


def test_format_explains_the_n_a_report_when_nothing_is_verified(tmp_path):
    banks = tmp_path / "banks"
    banks.mkdir()
    (banks / "v2.yaml").write_text(
        BANK_B.replace("status: verified", "status: unverified")
    )
    out = format_coverage(build_coverage(banks))
    assert "Nothing is verified" in out
    assert "`verified deterministic n/a`" in out
    assert "reviewers: none yet" in out
    assert "can feed a verified score" not in out


def test_detail_listing_is_off_by_default(tmp_path):
    cov = build_coverage(_banks(tmp_path))
    assert "per question:" not in format_coverage(cov)
    assert "per question:" in format_coverage(cov, detail=True)


def test_detail_shows_status_reviewer_and_date_per_question(tmp_path):
    out = format_coverage(build_coverage(_banks(tmp_path)), detail=True)
    assert "v1-Q1" in out and "Oscar R." in out and "2026-08-28" in out
    # An untouched question renders placeholders, never a blank column.
    assert "v1-Q4" in out
    line = next(l for l in out.splitlines() if l.startswith("v1-Q4"))
    assert line.split() == ["v1-Q4", "v1", "unverified", "-", "-", "-"]


def test_empty_banks_dir_does_not_divide_by_zero(tmp_path):
    banks = tmp_path / "banks"
    banks.mkdir()
    cov = build_coverage(banks)
    assert cov.overall.total == 0
    assert cov.overall.reviewed_pct == 0.0
    assert "no questions found" in format_coverage(cov)
