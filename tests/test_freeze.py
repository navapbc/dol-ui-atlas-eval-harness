# tests/test_freeze.py
from pathlib import Path

from atlas_eval.cli import main
from atlas_eval.dataset import compute_question_sha256, load_bank

BANK = """version: v1
agent: engineering_onboarding_specialist
corpus: quick_space_ca7_daily_s3
questions:
  - id: v1-Q1
    text: first question
    type: retrieval
    expected_stance: answer
    ground_truth: |
      Multi-line ground truth
      that must survive freezing.
    checks:
      required_all: [DXCBDA2R]
"""


def _write(tmp_path):
    p = tmp_path / "v1.yaml"
    p.write_text(BANK)
    return p


def test_freeze_writes_date_and_hash(tmp_path, capsys):
    p = _write(tmp_path)
    assert main(["freeze", "--bank", str(p), "--date", "2026-07-27"]) == 0
    bank = load_bank(p)
    assert str(bank.frozen_on) == "2026-07-27"
    assert bank.question_sha256 == compute_question_sha256(bank)
    assert "v1" in capsys.readouterr().out


def test_freeze_preserves_block_scalars_and_checks(tmp_path):
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    text = p.read_text()
    assert "ground_truth: |" in text, "block scalar must not be reflowed"
    assert "that must survive freezing." in text
    assert "DXCBDA2R" in text


def test_frozen_bank_then_validates_clean(tmp_path):
    from atlas_eval.validation import validate_bank
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    assert validate_bank(load_bank(p), "v1.yaml") == []


def test_refreeze_after_text_edit_changes_the_hash(tmp_path):
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    first = load_bank(p).question_sha256
    p.write_text(p.read_text().replace("first question", "first question, reworded"))
    main(["freeze", "--bank", str(p), "--date", "2026-07-28", "--force"])
    assert load_bank(p).question_sha256 != first


def test_refreeze_without_force_refuses_and_writes_nothing(tmp_path, capsys):
    p = _write(tmp_path)
    main(["freeze", "--bank", str(p), "--date", "2026-07-27"])
    before = p.read_text()
    exit_code = main(["freeze", "--bank", str(p), "--date", "2026-07-28"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "already frozen" in out
    assert "--force" in out
    assert p.read_text() == before, "must not write anything without --force"


def test_freeze_refuses_a_bank_with_validation_issues(tmp_path, capsys):
    p = tmp_path / "v1.yaml"
    p.write_text(BANK + """  - id: v1-Q1
    text: duplicate id
    type: retrieval
    expected_stance: answer
    ground_truth: gt
""")
    assert main(["freeze", "--bank", str(p), "--date", "2026-07-27"]) == 1
    assert "DUPLICATE_ID" in capsys.readouterr().out
    assert "frozen_on" not in p.read_text(), "must not freeze an invalid bank"
