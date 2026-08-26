import pytest
from pydantic import ValidationError

from atlas_eval.models import (
    Bank, Checks, Question, QuestionType, Stance, Verification, VerificationStatus,
)


def _q(**over):
    base = dict(
        id="v1-Q1",
        text="How does the weekly certification batch process flow?",
        type=QuestionType.RETRIEVAL,
        expected_stance=Stance.ANSWER,
        ground_truth="End-to-end flow across jobs and programs.",
    )
    base.update(over)
    return Question(**base)


def test_question_defaults_are_empty_not_shared():
    a, b = _q(), _q(id="v1-Q2")
    a.checks.forbidden.append("ETA-227")
    assert b.checks.forbidden == [], "default lists must not be shared between instances"
    assert a.verification.status is VerificationStatus.UNVERIFIED
    assert a.verification.verified_by is None
    assert a.after is None
    assert a.type_note is None


def test_question_rejects_unknown_type():
    with pytest.raises(ValidationError):
        _q(type="retrieval (multi-hop chain)")


def test_question_rejects_unknown_field():
    with pytest.raises(ValidationError):
        _q(expected_stace=Stance.ANSWER)


def test_all_thirteen_types_and_four_stances_exist():
    assert {t.value for t in QuestionType} == {
        "retrieval", "rule_logic", "data_flow", "gap_probe", "hallucination_bait",
        "absence_probe", "term_redirect", "acronym_check", "scope_boundary",
        "out_of_kb", "cross_space", "generation_probe", "handoff_probe",
    }
    assert {s.value for s in Stance} == {"answer", "hedge", "refuse", "redirect"}
    assert {v.value for v in VerificationStatus} == {
        "unverified", "verified", "rejected", "needs-sme",
    }


def test_bank_holds_questions_and_optional_freeze():
    bank = Bank(
        version="v1", agent="engineering_onboarding_specialist",
        corpus="quick_space_ca7_daily_s3", questions=[_q()],
    )
    assert bank.frozen_on is None and bank.question_sha256 is None
    assert bank.questions[0].id == "v1-Q1"


def test_checks_accept_all_four_lists():
    c = Checks(required_all=["ACP"], required_any=["Accelerated Collection Process"],
               forbidden=["ETA-227"], expect_citations=["UIMB0730"])
    assert c.expect_citations == ["UIMB0730"]
