import pytest

from atlas_eval.models import Checks, Question, QuestionType, Stance
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric, score_answer


def _q(**over):
    base = dict(
        id="v3-Q1", text="Describe the Automated Collection Process.",
        type=QuestionType.TERM_REDIRECT, expected_stance=Stance.REDIRECT,
        ground_truth="Maps to the Accelerated Collection Process.",
    )
    base.update(over)
    return Question(**base)


def test_all_checks_satisfied_passes():
    q = _q(checks=Checks(required_all=["ACP"],
                         required_any=["Accelerated Collection Process"],
                         forbidden=["ETA-227"],
                         expect_citations=["UIMB0730", "L2ACPD"]))
    s = score_answer(q, "The ACP, or Accelerated Collection Process, is documented "
                        "in UIMB0730 and driven by the L2ACPD stream.")
    assert s.required_all_pass and s.required_any_pass and s.forbidden_pass
    assert s.citation_recall == 1.0
    assert s.deterministic_pass is True
    assert s.question_id == "v3-Q1"


def test_matching_is_case_and_whitespace_insensitive():
    q = _q(checks=Checks(required_all=["Accelerated Collection Process"]))
    s = score_answer(q, "the   accelerated\ncollection    PROCESS applies")
    assert s.required_all_pass and s.deterministic_pass


def test_missing_required_all_fails_and_is_reported():
    q = _q(checks=Checks(required_all=["ACP", "DOR"]))
    s = score_answer(q, "The ACP handles collections.")
    assert s.required_all_pass is False
    assert s.missing_required == ["DOR"]
    assert s.deterministic_pass is False


def test_required_any_needs_only_one():
    q = _q(checks=Checks(required_any=["Accelerated Collection Process", "ACP"]))
    assert score_answer(q, "It is the ACP.").required_any_pass is True


def test_required_any_all_absent_fails():
    q = _q(checks=Checks(required_any=["Accelerated Collection Process", "ACP"]))
    s = score_answer(q, "It is a collections workflow.")
    assert s.required_any_pass is False
    assert s.deterministic_pass is False


def test_forbidden_term_present_fails_and_is_reported():
    q = _q(checks=Checks(forbidden=["ETA-227"]))
    s = score_answer(q, "This is the ETA-227 reporting process.")
    assert s.forbidden_pass is False
    assert s.present_forbidden == ["ETA-227"]
    assert s.deterministic_pass is False


def test_partial_citation_recall_reported_but_does_not_pass():
    q = _q(checks=Checks(expect_citations=["UIMB0730", "UIMB0731", "L2ACPD"]))
    s = score_answer(q, "See UIMB0730 and UIMB0731.")
    assert s.citation_recall == pytest.approx(2 / 3)
    assert s.missing_citations == ["L2ACPD"]
    assert s.deterministic_pass is False


def test_no_expected_citations_gives_recall_one():
    s = score_answer(_q(checks=Checks(required_all=["ACP"])), "The ACP.")
    assert s.citation_recall == 1.0
    assert s.deterministic_pass


def test_empty_checks_pass_vacuously():
    s = score_answer(_q(), "anything at all")
    assert s.deterministic_pass is True
    assert (s.missing_required, s.present_forbidden, s.missing_citations) == ([], [], [])


def test_stance_unobserved_is_none_and_does_not_fail():
    s = score_answer(_q(), "anything")
    assert s.stance_pass is None
    assert s.deterministic_pass is True


def test_observed_stance_matching_passes():
    s = score_answer(_q(expected_stance=Stance.REFUSE), "I cannot find that.",
                     observed_stance=Stance.REFUSE)
    assert s.stance_pass is True and s.deterministic_pass is True


def test_observed_stance_mismatch_fails_even_with_right_content():
    # A gap probe answered with confident invented detail fails on stance
    # even when it names a real program.
    q = _q(type=QuestionType.GAP_PROBE, expected_stance=Stance.HEDGE,
           checks=Checks(required_all=["Table 109"]))
    s = score_answer(q, "Table 109 contains codes 01 through 47.",
                     observed_stance=Stance.ANSWER)
    assert s.required_all_pass is True
    assert s.stance_pass is False
    assert s.deterministic_pass is False


def test_substring_matching_is_literal_not_semantic():
    # "collection process" must not satisfy a check for the full proper name.
    q = _q(checks=Checks(required_all=["Accelerated Collection Process"]))
    assert score_answer(q, "an automated collection process").required_all_pass is False


def test_rubric_dimensions_and_total():
    assert RUBRIC_DIMENSIONS == (
        "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    )
    r = Rubric(citations=2, correctness=1, gap_honesty=1, scope_discipline=1, clarity=2)
    assert r.total == 7


def test_rubric_total_is_none_until_fully_scored():
    assert Rubric(citations=2).total is None
    assert Rubric().total is None


def test_rubric_rejects_out_of_range():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Rubric(citations=3)


def test_rubric_records_who_scored_and_who_confirmed():
    r = Rubric(citations=2, correctness=2, gap_honesty=2, scope_discipline=2, clarity=2,
               scored_by="claude-opus-5")
    assert r.scored_by == "claude-opus-5"
    assert r.confirmed_by is None
    assert r.is_confirmed is False

    r.confirmed_by = "Michael"
    assert r.is_confirmed is True


def test_rubric_defaults_have_no_provenance():
    r = Rubric()
    assert r.scored_by is None and r.confirmed_by is None and r.is_confirmed is False


def test_scoring_module_imports_nothing_networked():
    # The deterministic scorer must stay stable and offline. LLM-drafted rubric
    # values arrive from the audit workflow; the scorer never fetches them.
    import atlas_eval.scoring as mod
    src = open(mod.__file__).read()
    for banned in ("requests", "boto3", "httpx", "urllib", "anthropic", "openai", "socket"):
        assert banned not in src, f"scoring must not reference {banned}"
