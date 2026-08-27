from datetime import datetime

from atlas_eval.adapters.base import Response
from atlas_eval.models import Question, QuestionType, Stance
from atlas_eval.runs import RunMeta, RunStatus
from atlas_eval.transcript import render_transcript


def _meta(**over):
    base = dict(
        run_id="2026-08-27_0900_quick_v3", backend="quick", transport="playwright",
        bank_version="v3", question_sha256="a" * 64,
        agent="engineering_onboarding_specialist",
        agent_id="093ac4e3-0712-481e-af95-9ddc5e4fc734",
        conversation_id="0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8",
        started_at=datetime(2026, 8, 27, 9, 0), finished_at=datetime(2026, 8, 27, 9, 30),
        status=RunStatus.COMPLETE,
    )
    base.update(over)
    return RunMeta(**base)


def _q(qid, text, after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


def _r(qid, answer, minute):
    return Response(question_id=qid, answer=answer,
                    asked_at=datetime(2026, 8, 27, 9, minute))


def test_header_carries_the_facts_needed_to_reinterpret_a_score():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question")], [_r("v3-Q1", "first answer", 5)],
        {"model_chip": "Advanced"},
    )
    for expected in ("2026-08-27_0900_quick_v3", "quick", "playwright", "v3",
                     "engineering_onboarding_specialist",
                     "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8", "Advanced"):
        assert expected in text, expected


def test_questions_and_answers_appear_in_asked_order():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question"), _q("v3-Q2", "second question", after="v3-Q1")],
        [_r("v3-Q1", "first answer", 5), _r("v3-Q2", "second answer", 8)], {},
    )
    assert text.index("first question") < text.index("second question")
    assert text.index("first answer") < text.index("second answer")


def test_after_dependency_is_called_out():
    # A later reader must be able to see that Q2's answer only means anything
    # because Q1 immediately preceded it.
    text = render_transcript(
        _meta(), [_q("v3-Q1", "q one"), _q("v3-Q2", "q two", after="v3-Q1")],
        [_r("v3-Q1", "a one", 5), _r("v3-Q2", "a two", 8)], {},
    )
    assert "after v3-Q1" in text


def test_unanswered_question_is_marked_not_silently_dropped():
    text = render_transcript(
        _meta(status=RunStatus.INCOMPLETE, finished_at=None),
        [_q("v3-Q1", "q one"), _q("v3-Q2", "q two")], [_r("v3-Q1", "a one", 5)], {},
    )
    assert "q two" in text
    assert "NO ANSWER" in text
    assert "incomplete" in text.lower()


def test_answer_text_is_never_truncated():
    long_answer = "X" * 9000
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", long_answer, 5)], {})
    assert long_answer in text


def test_is_markdown_with_one_top_level_heading():
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", "a", 5)], {})
    assert text.startswith("# ")
    assert sum(1 for line in text.splitlines() if line.startswith("# ")) == 1
