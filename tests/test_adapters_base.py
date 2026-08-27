from datetime import datetime

import pytest
from pydantic import ValidationError

from atlas_eval.adapters.base import AskResult, Backend, Response, TransportError
from atlas_eval.models import Question, QuestionType, Stance
from tests.adapter_conformance import assert_backend_conformance


def _q(qid="v1-Q1"):
    return Question(id=qid, text="t", type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt")


def test_response_defaults():
    r = Response(question_id="v1-Q1", answer="a", asked_at=datetime(2026, 8, 27, 9, 0))
    assert r.citations == []
    assert r.observed_stance is None


def test_response_default_citations_not_shared():
    a = Response(question_id="v1-Q1", answer="a", asked_at=datetime(2026, 8, 27, 9, 0))
    b = Response(question_id="v1-Q2", answer="b", asked_at=datetime(2026, 8, 27, 9, 1))
    a.citations.append("DXCBD87E")
    assert b.citations == []


def test_response_rejects_unknown_field():
    with pytest.raises(ValidationError):
        Response(question_id="v1-Q1", answer="a",
                 asked_at=datetime(2026, 8, 27, 9, 0), scored=True)


def test_ask_result_complete_and_failed_shapes():
    ok = AskResult(responses=[], conversation_id="c1", complete=True)
    assert ok.failure is None

    bad = AskResult(responses=[], conversation_id=None, complete=False,
                    failure="AUTH_REQUIRED: login redirect detected")
    assert bad.complete is False and "AUTH_REQUIRED" in bad.failure


def test_transport_error_carries_code_and_detail():
    err = TransportError("AUTH_REQUIRED", "redirected to /start/home?redirect_uri=")
    assert err.code == "AUTH_REQUIRED"
    assert "redirect_uri" in err.detail
    assert "AUTH_REQUIRED" in str(err)


def test_a_minimal_class_satisfies_the_protocol():
    class Fake:
        name = "fake"
        transport = "memory"

        def snapshot(self) -> dict:
            return {"agent": "fake"}

        def ask(self, questions):
            return AskResult(
                responses=[Response(question_id=q.id, answer=f"answer to {q.id}",
                                    asked_at=datetime(2026, 8, 27, 9, 0))
                           for q in questions],
                conversation_id="c1", complete=True,
            )

    fake = Fake()
    assert isinstance(fake, Backend)
    questions = [_q("v1-Q1"), _q("v1-Q2")]
    assert_backend_conformance(fake, questions)

    result = fake.ask(questions)
    assert [r.question_id for r in result.responses] == ["v1-Q1", "v1-Q2"]
    assert isinstance(fake.snapshot(), dict)


def test_conformance_helper_catches_non_ask_result_return():
    class ReturnsListBackend:
        name = "broken"
        transport = "memory"

        def snapshot(self) -> dict:
            return {}

        def ask(self, questions):
            # Satisfies runtime_checkable Backend, but violates the contract:
            # ask() must return an AskResult, not a bare list.
            return [
                Response(question_id=q.id, answer=f"answer to {q.id}",
                        asked_at=datetime(2026, 8, 27, 9, 0))
                for q in questions
            ]

    with pytest.raises(AssertionError):
        assert_backend_conformance(ReturnsListBackend(), [_q("v1-Q1"), _q("v1-Q2")])


def test_conformance_helper_catches_reordered_responses():
    class ReordersBackend:
        name = "broken"
        transport = "memory"

        def snapshot(self) -> dict:
            return {}

        def ask(self, questions):
            reordered = list(reversed(questions))
            return AskResult(
                responses=[
                    Response(question_id=q.id, answer=f"answer to {q.id}",
                            asked_at=datetime(2026, 8, 27, 9, 0))
                    for q in reordered
                ],
                conversation_id="c1", complete=True,
            )

    with pytest.raises(AssertionError):
        assert_backend_conformance(
            ReordersBackend(), [_q("v1-Q1"), _q("v1-Q2"), _q("v1-Q3")]
        )


def test_conformance_helper_catches_invented_question_id():
    class InventsIdBackend:
        name = "broken"
        transport = "memory"

        def snapshot(self) -> dict:
            return {}

        def ask(self, questions):
            responses = [
                Response(question_id=q.id, answer=f"answer to {q.id}",
                        asked_at=datetime(2026, 8, 27, 9, 0))
                for q in questions
            ]
            responses.append(Response(question_id="v1-Q999", answer="made up",
                                       asked_at=datetime(2026, 8, 27, 9, 0)))
            return AskResult(responses=responses, conversation_id="c1", complete=True)

    with pytest.raises(AssertionError):
        assert_backend_conformance(InventsIdBackend(), [_q("v1-Q1"), _q("v1-Q2")])


def test_conformance_helper_catches_incomplete_without_failure():
    class IncompleteNoFailureBackend:
        name = "broken"
        transport = "memory"

        def snapshot(self) -> dict:
            return {}

        def ask(self, questions):
            return AskResult(responses=[], conversation_id=None,
                             complete=False, failure=None)

    with pytest.raises(AssertionError):
        assert_backend_conformance(IncompleteNoFailureBackend(), [_q("v1-Q1")])


def test_adapters_never_import_the_scorer():
    # An adapter returns raw text; scoring is a separate layer that must not be
    # reachable from transport code, or a transport bug could alter a score.
    import atlas_eval.adapters.base as mod
    src = open(mod.__file__).read()
    assert "scoring" not in src
