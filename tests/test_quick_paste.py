import re
from datetime import datetime

import pytest

from atlas_eval.adapters.quick_paste import (
    PLACEHOLDER, QuickPasteBackend, parse_pasted_transcript, render_prompt_sheet,
)
from atlas_eval.models import Question, QuestionType, Stance
from tests.adapter_conformance import assert_backend_conformance

ASKED = datetime(2026, 8, 27, 9, 0)


def _q(qid, text="question text", after=None):
    return Question(id=qid, text=text, type=QuestionType.RETRIEVAL,
                    expected_stance=Stance.ANSWER, ground_truth="gt", after=after)


def _marker(question_id: str) -> str:
    return f"<!-- atlas:answer {question_id} -->"


def _fill_sheet(sheet: str, answers: dict[str, str]) -> str:
    """Substitute the placeholder after each question's marker with a real answer."""
    filled = sheet
    for qid, answer in answers.items():
        marker = _marker(qid)
        pattern = re.escape(marker) + r"\n\n" + re.escape(PLACEHOLDER)
        filled, n = re.subn(pattern, lambda m, a=answer, mk=marker: f"{mk}\n\n{a}", filled, count=1)
        assert n == 1, f"placeholder for {qid} not found exactly once in sheet"
    return filled


def test_prompt_sheet_lists_questions_in_given_order_with_ids():
    sheet = render_prompt_sheet([_q("v3-Q1", "first"), _q("v3-Q2", "second", after="v3-Q1")])
    assert sheet.index("v3-Q1") < sheet.index("v3-Q2")
    assert "first" in sheet and "second" in sheet


def test_prompt_sheet_flags_the_immediately_after_constraint():
    # The operator must not interleave anything, or the probe is destroyed.
    sheet = render_prompt_sheet([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert "immediately after v3-Q1" in sheet
    assert "same conversation" in sheet.lower()


def test_prompt_sheet_emits_a_marker_and_a_conversation_slot_for_every_question():
    sheet = render_prompt_sheet([_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])
    assert _marker("v3-Q1") in sheet
    assert _marker("v3-Q2") in sheet
    assert "conversation:" in sheet


def test_parse_extracts_answers_by_marker():
    text = (
        f"{_marker('v3-Q1')}\nThe ACP is the Accelerated Collection Process.\n\n"
        f"{_marker('v3-Q2')}\nACP.\n"
    )
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is True
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]
    assert "Accelerated Collection Process" in result.responses[0].answer


def test_parse_preserves_multi_paragraph_answers_and_code_blocks():
    answer = "Line one.\n\n```\nCOMPUTE WS-PWBR1 = (BP88-WBR * 1.2)\n```\n\nLine two."
    text = f"{_marker('v3-Q1')}\n{answer}\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == answer.strip()


def test_parse_is_tolerant_of_marker_whitespace_and_case():
    text = "<!--   atlas:answer   V3-q1   -->\nan answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.responses[0].answer.strip() == "an answer"


def test_missing_answer_yields_incomplete_not_a_silent_gap():
    text = f"{_marker('v3-Q1')}\nonly the first answer\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]


def test_empty_answer_body_counts_as_missing():
    text = f"{_marker('v3-Q1')}\nreal answer\n\n{_marker('v3-Q2')}\n   \n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure


def test_unknown_id_at_top_level_is_reported_not_ignored():
    # A stray/mistyped marker seen before any real answer has been opened is
    # a genuine operator error, not incidental content, and must be surfaced.
    text = f"{_marker('v9-Q9')}\nstray\n\n{_marker('v3-Q1')}\na\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.complete is False
    assert "v9-Q9" in result.failure


def test_responses_come_back_in_asked_order_not_paste_order():
    text = f"{_marker('v3-Q2')}\nsecond\n\n{_marker('v3-Q1')}\nfirst\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert [r.question_id for r in result.responses] == ["v3-Q1", "v3-Q2"]


def test_conversation_id_is_read_when_the_operator_supplies_it():
    text = f"conversation: 0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8\n\n{_marker('v3-Q1')}\na\n"
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.conversation_id == "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8"


def test_backend_satisfies_the_protocol_and_never_scores():
    backend = QuickPasteBackend(
        agent="engineering_onboarding_specialist",
        snapshot_data={"agent": {"Name": "Engineering Onboarding Specialist"}},
        transcript_text=f"{_marker('v3-Q1')}\nan answer\n",
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
        transcript_text=f"{_marker('v3-Q2')}\nsecond\n\n{_marker('v3-Q1')}\nfirst\n",
    )
    assert_backend_conformance(backend, [_q("v3-Q1"), _q("v3-Q2", after="v3-Q1")])


# --- Reproduced-defect regression tests -------------------------------------

def test_marker_with_unknown_id_inside_an_answer_stays_content():
    # Reproduces Finding 1's first scenario in the new marker form: an
    # incidental marker-shaped line with an unrecognised id, occurring
    # *inside* an already-open answer, must not truncate the answer, drop
    # the lines after it, or be reported as an error.
    text = (
        f"{_marker('v3-Q1')}\n"
        "The ACP is the Accelerated Collection Process.\n\n"
        f"{_marker('Example')}\n"
        "This sentence must survive; it is still part of the v3-Q1 answer.\n\n"
        f"{_marker('v3-Q2')}\n"
        "second answer\n"
    )
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is True, result.failure
    assert _marker("Example") in result.responses[0].answer
    assert "This sentence must survive" in result.responses[0].answer
    assert result.responses[1].answer.strip() == "second answer"


def test_fenced_code_containing_a_real_marker_does_not_split_the_answer():
    # Reproduces Finding 1's second scenario: a fenced code block containing
    # a bare line that looks exactly like a real question's marker must not
    # be treated as a delimiter, and neither answer may be corrupted.
    text = (
        f"{_marker('v3-Q1')}\n"
        "Here is a snippet:\n\n"
        "```\n"
        f"{_marker('v3-Q2')}\n"
        "SOME-CODE HERE\n"
        "```\n\n"
        "end of answer.\n\n"
        f"{_marker('v3-Q2')}\n"
        "real second answer\n"
    )
    result = parse_pasted_transcript(text, [_q("v3-Q1"), _q("v3-Q2")], ASKED)
    assert result.complete is True, result.failure
    assert _marker("v3-Q2") in result.responses[0].answer
    assert "SOME-CODE HERE" in result.responses[0].answer
    assert "end of answer." in result.responses[0].answer
    assert result.responses[1].answer.strip() == "real second answer"


def test_half_filled_generated_sheet_reports_missing_and_never_stores_placeholder():
    # Reproduces Finding 2: returning the generated sheet with only some
    # answers filled in must report the unfilled ids, not store the
    # placeholder text as a real answer.
    questions = [_q("v3-Q1", "first"), _q("v3-Q2", "second", after="v3-Q1")]
    sheet = render_prompt_sheet(questions)
    filled = _fill_sheet(sheet, {"v3-Q1": "a real answer for Q1"})

    result = parse_pasted_transcript(filled, questions, ASKED)
    assert result.complete is False
    assert "v3-Q2" in result.failure
    assert [r.question_id for r in result.responses] == ["v3-Q1"]
    assert result.responses[0].answer.strip() == "a real answer for Q1"
    assert all(PLACEHOLDER not in r.answer for r in result.responses)


def test_conversation_id_at_end_of_document_is_read_and_excluded_from_answers():
    # Reproduces Finding 3: the conversation line must be read no matter
    # where it sits, and must never become part of an answer's body.
    text = (
        f"{_marker('v3-Q1')}\nan answer\n\n"
        "conversation: 0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8\n"
    )
    result = parse_pasted_transcript(text, [_q("v3-Q1")], ASKED)
    assert result.conversation_id == "0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8"
    assert result.complete is True, result.failure
    assert result.responses[0].answer.strip() == "an answer"
    assert "conversation:" not in result.responses[0].answer


def test_generated_sheet_round_trips_when_fully_filled():
    # The property that was missing: what render_prompt_sheet produces, once
    # every placeholder is replaced with a real answer, must parse back
    # cleanly with each answer mapped to the right question.
    questions = [
        _q("v3-Q1", "What is the ACP?"),
        _q("v3-Q2", "What does ACP stand for?", after="v3-Q1"),
        _q("v3-Q3", "third question text"),
    ]
    sheet = render_prompt_sheet(questions)
    answers = {
        "v3-Q1": "The ACP is the Accelerated Collection Process.",
        "v3-Q2": "It stands for Accelerated Collection Process.\n\n```\nCOMPUTE X = 1\n```",
        "v3-Q3": "a plain answer",
    }
    filled = _fill_sheet(sheet, answers)

    result = parse_pasted_transcript(filled, questions, ASKED)
    assert result.complete is True, result.failure
    by_id = {r.question_id: r.answer.strip() for r in result.responses}
    for qid, answer in answers.items():
        assert by_id[qid] == answer.strip()
