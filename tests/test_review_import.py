from datetime import date
from pathlib import Path

from openpyxl import load_workbook

from atlas_eval.dataset import load_bank
from atlas_eval.models import VerificationStatus
from atlas_eval.review import export_review, import_review

BANK_YAML = """version: v3
frozen_on: 2026-08-03
question_sha256: PLACEHOLDER
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v3-Q1
    text: Describe the Automated Collection Process.
    type: term_redirect
    type_note: term-redirect
    expected_stance: redirect
    ground_truth: |
      Maps to the Accelerated Collection Process (ACP).
    checks:
      required_all: [ACP]
      forbidden: [ETA-227]
  - id: v3-Q2
    after: v3-Q1
    text: What does the acronym ACP stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: |
      Accelerated Collection Process.
"""


BANK_YAML_V4 = """version: v4
frozen_on: 2026-08-03
question_sha256: PLACEHOLDER
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v4-Q1
    text: What is the ETA-227?
    type: term_redirect
    type_note: term-redirect
    expected_stance: redirect
    ground_truth: |
      A quarterly report on collection activity.
    checks:
      required_all: [ETA-227]
  - id: v4-Q2
    after: v4-Q1
    text: What does the acronym ETA stand for?
    type: acronym_check
    expected_stance: answer
    ground_truth: |
      Employment and Training Administration.
"""


def _write_bank(d, name, yaml_text):
    from atlas_eval.dataset import compute_question_sha256
    p = d / name
    p.write_text(yaml_text)
    bank = load_bank(p)
    p.write_text(yaml_text.replace("PLACEHOLDER", compute_question_sha256(bank)))
    return p


def _banks_dir(tmp_path):
    d = tmp_path / "banks"
    d.mkdir()
    _write_bank(d, "v3.yaml", BANK_YAML)
    return d


def _two_banks_dir(tmp_path):
    d = tmp_path / "banks"
    d.mkdir()
    _write_bank(d, "v3.yaml", BANK_YAML)
    _write_bank(d, "v4.yaml", BANK_YAML_V4)
    return d


def _sheet(path, edits):
    """Export then apply {question_id: {column: value}} edits in place."""
    wb = load_workbook(path)
    ws = wb["Review"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2):
        qid = row[0].value
        for col, value in edits.get(qid, {}).items():
            row[headers.index(col)].value = value
    wb.save(path)


def _roundtrip(tmp_path, edits):
    banks = _banks_dir(tmp_path)
    xlsx = tmp_path / "review.xlsx"
    export_review([load_bank(banks / "v3.yaml")], xlsx)
    _sheet(xlsx, edits)
    return banks, xlsx


def _roundtrip_multi(tmp_path, edits):
    banks = _two_banks_dir(tmp_path)
    xlsx = tmp_path / "review.xlsx"
    export_review([load_bank(banks / "v3.yaml"), load_bank(banks / "v4.yaml")], xlsx)
    _sheet(xlsx, edits)
    return banks, xlsx


def test_clean_roundtrip_leaves_the_file_byte_identical(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {})
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok and report.transitions == []
    assert report.unchanged == 2
    assert (banks / "v3.yaml").read_bytes() == before, "no verdicts means no write"


def test_yes_verdict_marks_verified(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"},
    })
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok
    assert [(t.question_id, t.new_status) for t in report.transitions] == [
        ("v3-Q1", VerificationStatus.VERIFIED)
    ]
    q1 = load_bank(banks / "v3.yaml").questions[0]
    assert q1.verification.status is VerificationStatus.VERIFIED
    assert q1.verification.verified_by == "Oscar"
    assert str(q1.verification.verified_on) == "2026-08-28"


def test_no_verdict_marks_rejected_and_keeps_the_question(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q2": {"accurate?": "no", "reviewer": "Oscar",
                  "comments": "No knowable answer; I did not know it either."},
    })
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    bank = load_bank(banks / "v3.yaml")
    assert len(bank.questions) == 2, "a rejected question is retained, not deleted"
    q2 = bank.questions[1]
    assert q2.verification.status is VerificationStatus.REJECTED
    assert "No knowable answer" in q2.verification.notes


def test_unsure_verdict_marks_needs_sme(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "unsure", "reviewer": "Oscar"}})
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert load_bank(banks / "v3.yaml").questions[0].verification.status is (
        VerificationStatus.NEEDS_SME
    )


def test_reviewer_comments_land_in_notes_and_never_in_ground_truth(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "no", "reviewer": "Oscar",
                  "comments": "Actually it is the Accelerated Collection Population."},
    })
    before_gt = load_bank(banks / "v3.yaml").questions[0].ground_truth
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    q1 = load_bank(banks / "v3.yaml").questions[0]
    assert "Accelerated Collection Population" in q1.verification.notes
    assert q1.ground_truth == before_gt, "import must never rewrite ground truth"


def test_edited_question_text_aborts_the_whole_import(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar",
                  "question": "Describe the ACP, reworded in Excel"},
        "v3-Q2": {"accurate?": "yes", "reviewer": "Oscar"},
    })
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("v3-Q1" in e and "question text" in e for e in report.errors)
    assert (banks / "v3.yaml").read_bytes() == before, "abort must write nothing at all"


def test_question_text_comparison_tolerates_whitespace_only_changes(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar",
                  "question": "  Describe the   Automated Collection Process.  "},
    })
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok, report.errors


def test_unknown_id_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {})
    wb = load_workbook(xlsx)
    wb["Review"].append(["v9-Q9", "a question from nowhere", "retrieval", "gt", "",
                         "yes", "Oscar", ""])
    wb.save(xlsx)
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("v9-Q9" in e for e in report.errors)


def test_invalid_accurate_value_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "probably", "reviewer": "O"}})
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("probably" in e for e in report.errors)


def test_verdict_without_a_reviewer_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes"}})
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert not report.ok
    assert any("reviewer" in e.lower() for e in report.errors)


def test_dry_run_reports_transitions_without_writing(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28), dry_run=True)
    assert report.ok and len(report.transitions) == 1
    assert (banks / "v3.yaml").read_bytes() == before


def test_import_preserves_frozen_hash_and_formatting(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    before = load_bank(banks / "v3.yaml").question_sha256
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    text = (banks / "v3.yaml").read_text()
    assert load_bank(banks / "v3.yaml").question_sha256 == before
    assert "ground_truth: |" in text, "block scalars must survive the rewrite"
    assert "after: v3-Q2" not in text and "after: v3-Q1" in text


def test_import_is_idempotent(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    first = (banks / "v3.yaml").read_bytes()
    second_report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert second_report.transitions == []
    assert (banks / "v3.yaml").read_bytes() == first


def test_multi_bank_verdicts_land_in_the_correct_file(tmp_path):
    banks, xlsx = _roundtrip_multi(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"},
        "v4-Q1": {"accurate?": "no", "reviewer": "Priya", "comments": "Needs a source."},
    })
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))
    assert report.ok, report.errors

    v3 = load_bank(banks / "v3.yaml")
    v4 = load_bank(banks / "v4.yaml")
    assert v3.questions[0].id == "v3-Q1"
    assert v3.questions[0].verification.status is VerificationStatus.VERIFIED
    assert v3.questions[0].verification.verified_by == "Oscar"
    assert v4.questions[0].id == "v4-Q1"
    assert v4.questions[0].verification.status is VerificationStatus.REJECTED
    assert v4.questions[0].verification.verified_by == "Priya"

    # Verdicts must not bleed into the sibling bank's untouched questions.
    assert v3.questions[1].verification.status is VerificationStatus.UNVERIFIED
    assert v4.questions[1].verification.status is VerificationStatus.UNVERIFIED


def test_invalid_row_in_one_bank_aborts_writes_to_every_bank(tmp_path):
    """The realistic corpus is several bank files reviewed in one sheet; a single
    bad row anywhere must block writes to all of them, not just its own file."""
    banks, xlsx = _roundtrip_multi(tmp_path, {
        "v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"},
        "v4-Q1": {"accurate?": "yes"},  # missing reviewer name
    })
    before_v3 = (banks / "v3.yaml").read_bytes()
    before_v4 = (banks / "v4.yaml").read_bytes()

    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))

    assert not report.ok
    assert any("v4-Q1" in e and "reviewer" in e.lower() for e in report.errors)
    assert (banks / "v3.yaml").read_bytes() == before_v3, (
        "a validation failure in v4 must abort v3's writes too"
    )
    assert (banks / "v4.yaml").read_bytes() == before_v4


def test_duplicate_id_in_sheet_aborts(tmp_path):
    banks, xlsx = _roundtrip(tmp_path, {"v3-Q1": {"accurate?": "yes", "reviewer": "Oscar"}})
    wb = load_workbook(xlsx)
    ws = wb["Review"]
    duplicate_row = [c.value for c in ws[2]]
    assert duplicate_row[0] == "v3-Q1"
    ws.append(duplicate_row)
    wb.save(xlsx)

    before = (banks / "v3.yaml").read_bytes()
    report = import_review(xlsx, banks, reviewed_on=date(2026, 8, 28))

    assert not report.ok
    assert any(
        "v3-Q1" in e and "duplicate" in e.lower() and "at most once" in e.lower()
        for e in report.errors
    )
    assert (banks / "v3.yaml").read_bytes() == before, "abort must write nothing at all"
