from pathlib import Path

from atlas_eval.cli import main
from atlas_eval.dataset import compute_question_sha256
from atlas_eval.models import Bank, Question, QuestionType, Stance
from atlas_eval.validation import validate_bank, validate_dir


def _bank(**over):
    base = dict(
        version="v1", agent="a", corpus="c",
        questions=[
            Question(id="v1-Q1", text="first", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt"),
            Question(id="v1-Q2", text="second", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt"),
        ],
    )
    base.update(over)
    return Bank(**base)


def _codes(issues):
    return sorted(i.code for i in issues)


def test_clean_unfrozen_bank_has_no_issues():
    assert validate_bank(_bank(), "v1.yaml") == []


def test_frozen_bank_with_matching_hash_is_clean():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    assert validate_bank(b, "v1.yaml") == []


def test_frozen_bank_with_edited_question_fails_hash():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    b.questions[0].text = "first, but reworded after freezing"
    issues = validate_bank(b, "v1.yaml")
    assert _codes(issues) == ["FROZEN_HASH_MISMATCH"]
    assert "bump the version" in issues[0].message


def test_frozen_bank_without_hash_is_an_issue():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    assert _codes(validate_bank(b, "v1.yaml")) == ["FROZEN_HASH_MISSING"]


def test_editing_ground_truth_after_freezing_is_allowed():
    b = _bank()
    b.frozen_on = __import__("datetime").date(2026, 8, 3)
    b.question_sha256 = compute_question_sha256(b)
    b.questions[0].ground_truth = "corrected after the run, as v3's key was"
    b.questions[0].checks.forbidden.append("ETA-227")
    assert validate_bank(b, "v1.yaml") == []


def test_duplicate_id_within_bank():
    b = _bank()
    b.questions[1].id = "v1-Q1"
    issues = validate_bank(b, "v1.yaml")
    assert "DUPLICATE_ID" in _codes(issues)


def test_id_prefix_must_match_version():
    b = _bank()
    b.questions[1].id = "v2-Q2"
    issues = validate_bank(b, "v1.yaml")
    assert "ID_PREFIX_MISMATCH" in _codes(issues)
    assert issues[0].question_id == "v2-Q2"


def test_empty_bank_is_an_issue():
    assert _codes(validate_bank(_bank(questions=[]), "v1.yaml")) == ["EMPTY_BANK"]


def test_run_order_problems_surface_as_issues():
    b = _bank()
    b.questions[1].after = "v1-Q99"
    assert "AFTER_DANGLING" in _codes(validate_bank(b, "v1.yaml"))


def test_id_with_embedded_space_is_malformed():
    b = _bank()
    b.questions[1].id = "v1-Q 2"
    issues = validate_bank(b, "v1.yaml")
    assert "ID_MALFORMED" in _codes(issues)


def test_id_with_embedded_tab_is_malformed():
    b = _bank()
    b.questions[1].id = "v1-Q2\t"
    issues = validate_bank(b, "v1.yaml")
    assert "ID_MALFORMED" in _codes(issues)


def test_id_with_embedded_newline_is_malformed():
    b = _bank()
    b.questions[1].id = "v1-Q2\n"
    issues = validate_bank(b, "v1.yaml")
    assert "ID_MALFORMED" in _codes(issues)


def test_normal_id_is_not_malformed():
    b = _bank()
    issues = validate_bank(b, "v1.yaml")
    assert "ID_MALFORMED" not in _codes(issues)


def test_validate_dir_reports_duplicate_ids_across_banks(tmp_path):
    for v in ("v1", "v2"):
        (tmp_path / f"{v}.yaml").write_text(
            f"version: {v}\nagent: a\ncorpus: c\nquestions:\n"
            "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
            "    expected_stance: answer\n    ground_truth: gt\n"
        )
    codes = _codes(validate_dir(tmp_path))
    assert "DUPLICATE_ID" in codes


def test_validate_dir_turns_schema_errors_into_issues(tmp_path):
    (tmp_path / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: nonsense\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    issues = validate_dir(tmp_path)
    assert _codes(issues) == ["SCHEMA"]
    assert "v1-Q1" in issues[0].message


def test_cli_validate_exit_codes(tmp_path, capsys):
    good = tmp_path / "banks"
    good.mkdir()
    (good / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    assert main(["validate", "--banks", str(good)]) == 0
    assert "1 bank" in capsys.readouterr().out

    (good / "v1.yaml").write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
        "  - id: v1-Q1\n    text: u\n    type: retrieval\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    assert main(["validate", "--banks", str(good)]) == 1
    assert "DUPLICATE_ID" in capsys.readouterr().out
