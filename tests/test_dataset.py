import datetime
from pathlib import Path

import pytest

from atlas_eval.dataset import (
    BankLoadError, compute_question_sha256, load_all_banks, load_bank, normalize_ws,
)
from atlas_eval.models import Bank, Question, QuestionType, Stance

FIXTURES = Path(__file__).parent / "fixtures" / "banks"


def _bank(*pairs, version="v1"):
    return Bank(
        version=version, agent="a", corpus="c",
        questions=[
            Question(id=i, text=t, type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt")
            for i, t in pairs
        ],
    )


def test_normalize_ws_collapses_and_lowercases():
    assert normalize_ws("  The   ACP\n\tflow ") == "the acp flow"


def test_hash_ignores_question_order():
    a = _bank(("v1-Q1", "first"), ("v1-Q2", "second"))
    b = _bank(("v1-Q2", "second"), ("v1-Q1", "first"))
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_ignores_whitespace_and_case_in_text():
    a = _bank(("v1-Q1", "Describe the ACP"))
    b = _bank(("v1-Q1", "describe   the\nacp"))
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_changes_when_question_text_changes():
    a = _bank(("v1-Q1", "Describe the ACP"))
    b = _bank(("v1-Q1", "Describe the ACP process"))
    assert compute_question_sha256(a) != compute_question_sha256(b)


def test_hash_changes_when_id_changes():
    assert compute_question_sha256(_bank(("v1-Q1", "x"))) != compute_question_sha256(
        _bank(("v1-Q9", "x"))
    )


def test_hash_ignores_ground_truth_and_checks():
    a = _bank(("v1-Q1", "x"))
    b = _bank(("v1-Q1", "x"))
    b.questions[0].ground_truth = "completely rewritten after freezing"
    b.questions[0].checks.forbidden.append("ETA-227")
    assert compute_question_sha256(a) == compute_question_sha256(b)


def test_hash_is_hex_sha256():
    h = compute_question_sha256(_bank(("v1-Q1", "x")))
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_hash_resists_delimiter_injection_across_id_and_text_boundary():
    # A tab/newline inside an id could, with a naive delimiter-joined payload,
    # impersonate the id/text or record separator and forge a collision
    # between two banks with genuinely different question sets.
    bank_a = _bank(("A", "B"), ("C", "D"))
    bank_b = _bank(("A\tb\nC", "D"))
    assert compute_question_sha256(bank_a) != compute_question_sha256(bank_b)


def test_hash_with_delimiter_bearing_id_is_deterministic():
    bank = _bank(("A\tb\nC", "D"))
    assert compute_question_sha256(bank) == compute_question_sha256(bank)


def test_load_bank_reads_nested_structure():
    bank = load_bank(FIXTURES / "mini.yaml")
    assert bank.version == "v1"
    assert [q.id for q in bank.questions] == ["v1-Q1", "v1-Q2"]
    q2 = bank.questions[1]
    assert q2.after == "v1-Q1"
    assert q2.type is QuestionType.TERM_REDIRECT
    assert q2.type_note == "term-redirect"
    assert q2.checks.forbidden == ["ETA-227"]
    assert q2.expected_stance is Stance.REDIRECT
    # Pin the ruamel round-trip paths: wrapper types (ScalarDate,
    # LiteralScalarString) must not leak past pydantic into plain builtins.
    assert bank.frozen_on == datetime.date(2026, 8, 3)
    assert type(bank.frozen_on) is datetime.date
    assert type(bank.sourcing) is str
    assert "Two-question fixture" in bank.sourcing
    assert type(bank.questions[0].ground_truth) is str


def test_load_bank_error_names_the_question(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "version: v1\nagent: a\ncorpus: c\nquestions:\n"
        "  - id: v1-Q1\n    text: t\n    type: nonsense\n"
        "    expected_stance: answer\n    ground_truth: gt\n"
    )
    with pytest.raises(BankLoadError) as exc:
        load_bank(bad)
    assert "v1-Q1" in str(exc.value)


def test_load_all_banks_sorts_numerically(tmp_path):
    for v in ("v10", "v2", "v1"):
        (tmp_path / f"{v}.yaml").write_text(
            f"version: {v}\nagent: a\ncorpus: c\nquestions:\n"
            f"  - id: {v}-Q1\n    text: t\n    type: retrieval\n"
            f"    expected_stance: answer\n    ground_truth: gt\n"
        )
    assert [b.version for b in load_all_banks(tmp_path)] == ["v1", "v2", "v10"]
