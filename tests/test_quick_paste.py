from datetime import datetime

import pytest

from atlas_eval.adapters.quick_paste import (
    QuickPasteBackend, parse_pasted_transcript, render_prompt_sheet,
)
from atlas_eval.models import Question, QuestionType, Stance
from tests.adapter_conformance import assert_backend_conformance

ASKED = datetime(2026, 8, 27, 9, 0)


def _q(qid, text="question text", after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


def test_prompt_sheet_lists_questions_in_given_order_with_ids():
    sheet = render_prompt_sheet([_q("v3-Q1", "first"), _q("v3-Q2", "second", after="v3-Q1")])
    assert sheet.index("v3-Q1") < sheet.index("v3-Q2")
    assert "first" in sheet and "second" in sheet


def test_prompt_sheet_flags_the_immediately_after_constraint():
    # The operator must not interleave anything, or the probe is destroyed.
    sheet = render_prompt_sheet([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert "immediately after v3-Q1" in sheet
    assert "same conversation" in sheet.lower()


def test_parse_extracts_answers_by_id_heading():
    text = "### v3-Q1\nThe ACP is the Accelerated Collection Process.\n\n### v3-Q2\nACP.\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is True
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]
    assert "Accelerated Collection Process" in result.responses[0].answer


def test_parse_preserves_multi_paragraph_answers_and_code_blocks():
    answer = "Line one.\n\n```\nCOMPUTE WS-PWBR1 = (BP88-WBR * 1.2)\n```\n\nLine two."
    text = f"### v3-Q1\n{answer}\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == answer.strip()


def test_parse_is_tolerant_of_heading_whitespace_and_case():
    text = "###   V3-q1  \nan answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == "an answer"


def test_missing_answer_yields_incomplete_not_a_silent_gap():
    text = "### v3-Q1\nonly the first answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_empty_answer_body_counts_as_missing():
    text = "### v3-Q1\nreal answer\n\n### v3-Q2\n   \n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure


def test_unknown_id_in_the_paste_is_reported_not_ignored():
    text = "### v3-Q1\na\n\n### v9-Q9\nstray\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.complete is False
    assert "v9-Q9" in result.failure


def test_responses_come_back_in_asked_order_not_paste_order():
    text = "### v3-Q2\nsecond\n\n### v3-Q1\nfirst\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]


def test_conversation_id_is_read_when_the_operator_supplies_it():
    text = "conversation: 0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8\n\n### v3-Q1\na\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.conversation_id == "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8"


def test_backend_satisfies_the_protocol_and_never_scores():
    backend = QuickPasteBackend(
        agent="engineering_onboarding_specialist",
        snapshot_data={"agent": {"Name": "Engineering Onboarding Specialist"}},
        transcript_text="### v3-Q1\nan answer\n",
    )
    assert (backend.name, backend.transport) == ("quick", "paste")
    assert backend.snapshot()["agent"]["Name"] == "Engineering Onboarding Specialist"
    result = backend.ask([_q("v3-Q1")])
    assert result.complete and result.responses[0].answer.strip() == "an answer"

    import atlas_eval.adapters.quick_paste as mod
    assert "scoring" not in open(mod.__file__).read()


def test_backend_conforms_to_the_backend_protocol():
    backend = QuickPasteBackend(
        agent="engineering_onboarding_specialist",
        snapshot_data={"agent": {"Name": "Engineering Onboarding Specialist"}},
        transcript_text="### v3-Q2\nsecond\n\n### v3-Q1\nfirst\n",
    )
    assert_backend_conformance(backend, [_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
