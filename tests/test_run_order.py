import pytest

from atlas_eval.dataset import RunOrderError, resolve_run_order
from atlas_eval.models import Bank, Question, QuestionType, Stance


def _bank(spec):
    """spec: list of (id, after)."""
    return Bank(
        version="v3", agent="a", corpus="c",
        questions=[
            Question(id=i, text=f"text {i}", type=QuestionType.RETRIEVAL,
                     expected_stance=Stance.ANSWER, ground_truth="gt", after=aft)
            for i, aft in spec
        ],
    )


def _ids(bank):
    return [q.id for q in resolve_run_order(bank)]


def test_no_dependencies_keeps_file_order():
    assert _ids(_bank([("Q1", None), ("Q2", None), ("Q3", None)])) == ["Q1", "Q2", "Q3"]


def test_dependent_question_runs_immediately_after_its_target():
    # Q3 declares after Q1, so it must sit between Q1 and Q2 despite file order.
    assert _ids(_bank([("Q1", None), ("Q2", None), ("Q3", "Q1")])) == ["Q1", "Q3", "Q2"]


def test_chain_of_three_stays_contiguous():
    order = _ids(_bank([("Q1", None), ("Q2", None), ("Q3", "Q1"), ("Q4", "Q3")]))
    assert order == ["Q1", "Q3", "Q4", "Q2"]


def test_v3_real_shape():
    # Q2 follows Q1, Q5 follows Q4, Q7 follows Q6 — the actual v3 constraints.
    order = _ids(_bank([
        ("Q1", None), ("Q2", "Q1"), ("Q3", None), ("Q4", None),
        ("Q5", "Q4"), ("Q6", None), ("Q7", "Q6"), ("Q8", None),
    ]))
    assert order == ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]
    assert order.index("Q2") == order.index("Q1") + 1
    assert order.index("Q5") == order.index("Q4") + 1
    assert order.index("Q7") == order.index("Q6") + 1


def test_every_question_appears_exactly_once():
    order = _ids(_bank([("Q1", None), ("Q2", "Q1"), ("Q3", "Q2"), ("Q4", None)]))
    assert sorted(order) == ["Q1", "Q2", "Q3", "Q4"]


def test_dangling_after_raises():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", None), ("Q2", "Q99")]))
    assert exc.value.code == "AFTER_DANGLING"
    assert exc.value.question_ids == ["Q2"]


def test_cycle_raises():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", "Q2"), ("Q2", "Q1")]))
    assert exc.value.code == "AFTER_CYCLE"
    assert set(exc.value.question_ids) == {"Q1", "Q2"}


def test_self_reference_is_a_cycle():
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", "Q1")]))
    assert exc.value.code == "AFTER_CYCLE"


def test_two_questions_after_the_same_target_is_ambiguous():
    # "immediately after" cannot be satisfied for both.
    with pytest.raises(RunOrderError) as exc:
        resolve_run_order(_bank([("Q1", None), ("Q2", "Q1"), ("Q3", "Q1")]))
    assert exc.value.code == "AFTER_AMBIGUOUS"
    assert set(exc.value.question_ids) == {"Q2", "Q3"}
