import re
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


def _r(qid, answer, minute, citations=None):
    return Response(question_id=qid, answer=answer,
                    asked_at=datetime(2026, 8, 27, 9, minute),
                    citations=citations or [])


def _sections(text: str) -> dict[str, str]:
    """Split a rendered transcript into {question_id: section_text} by '## ' headings."""
    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    out = {}
    for part in parts:
        heading_line, _, body = part.partition("\n")
        qid = heading_line.split(" ", 1)[0].strip()
        out[qid] = heading_line + "\n" + body
    return out


def test_header_carries_the_facts_needed_to_reinterpret_a_score():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question")], [_r("v3-Q1", "first answer", 5)],
        {"model_chip": "Advanced"},
    )
    header = text.split("\n## ", 1)[0]
    assert "- **Backend:** quick (transport: playwright)" in header
    assert "- **Bank:** v3 (`question_sha256` " in header
    assert "- **Agent:** engineering_onboarding_specialist" in header
    assert "- **Conversation:** `0f7d8a7d-21b5-4c8f-a278-42b98aa6fcf8`" in header
    assert "- **Model:** Advanced" in header
    assert header.startswith("# 2026-08-27_0900_quick_v3")


def test_questions_and_answers_appear_in_asked_order():
    text = render_transcript(
        _meta(), [_q("v3-Q1", "first question"), _q("v3-Q2", "second question", after="v3-Q1")],
        [_r("v3-Q1", "first answer", 5), _r("v3-Q2", "second answer", 8)], {},
    )
    assert text.index("first question") < text.index("second question")
    assert text.index("first answer") < text.index("second answer")


def test_answer_is_attached_to_its_own_question_not_a_neighbor():
    # The important failure mode: an answer rendered in the *wrong* section,
    # or a section that leaks a sibling's content.
    text = render_transcript(
        _meta(),
        [_q("v3-Q1", "q one"), _q("v3-Q2", "q two", after="v3-Q1")],
        [_r("v3-Q1", "UNIQUE_ANSWER_ONE", 5), _r("v3-Q2", "UNIQUE_ANSWER_TWO", 8)], {},
    )
    sections = _sections(text)
    assert "UNIQUE_ANSWER_ONE" in sections["v3-Q1"]
    assert "UNIQUE_ANSWER_TWO" not in sections["v3-Q1"]
    assert "UNIQUE_ANSWER_TWO" in sections["v3-Q2"]
    assert "UNIQUE_ANSWER_ONE" not in sections["v3-Q2"]


def test_after_dependency_is_called_out_on_the_dependent_heading():
    # A later reader must be able to see that Q2's answer only means anything
    # because Q1 immediately preceded it -- and that the note is on Q2's own
    # heading, not Q1's.
    text = render_transcript(
        _meta(), [_q("v3-Q1", "q one"), _q("v3-Q2", "q two", after="v3-Q1")],
        [_r("v3-Q1", "a one", 5), _r("v3-Q2", "a two", 8)], {},
    )
    sections = _sections(text)
    assert "after v3-Q1" in sections["v3-Q2"].splitlines()[0]
    assert "after v3-Q1" not in sections["v3-Q1"].splitlines()[0]


def test_unanswered_question_is_marked_not_silently_dropped():
    text = render_transcript(
        _meta(status=RunStatus.INCOMPLETE, finished_at=None),
        [_q("v3-Q1", "q one"), _q("v3-Q2", "q two")], [_r("v3-Q1", "a one", 5)], {},
    )
    sections = _sections(text)
    assert "NO ANSWER" in sections["v3-Q2"]
    assert "incomplete" in text.lower()


def test_answer_text_is_never_truncated():
    long_answer = "X" * 9000
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", long_answer, 5)], {})
    assert long_answer in text


def test_is_markdown_with_one_top_level_heading():
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", "a", 5)], {})
    assert text.startswith("# ")
    assert sum(1 for line in text.splitlines() if line.startswith("# ")) == 1


def test_citation_label_containing_a_comma_is_not_ambiguous():
    # ["Guide, p.4", "Sec 2.1"] must not render identically to three separate
    # citations -- the original two-item list must be recoverable.
    text = render_transcript(
        _meta(), [_q("v3-Q1", "q")],
        [_r("v3-Q1", "a", 5, citations=["Guide, p.4", "Sec 2.1"])], {},
    )
    sections = _sections(text)
    body = sections["v3-Q1"]
    assert "- Guide, p.4" in body
    assert "- Sec 2.1" in body
    # Exactly two citation bullets, not three items split on the comma.
    assert body.count("\n- ") == 2


# --- Adversarial: an answer's markdown must never be able to corrupt the
# rest of the document. Each case pairs a hostile Q1 answer with a normal Q2,
# and proves Q2's section is still intact and readable.

def _render_adversarial(hostile_answer: str) -> str:
    return render_transcript(
        _meta(),
        [_q("v3-Q1", "hostile question"), _q("v3-Q2", "second question", after="v3-Q1")],
        [_r("v3-Q1", hostile_answer, 5), _r("v3-Q2", "second answer, safe and sound", 8)],
        {},
    )


def _assert_structurally_sound(text: str):
    fence_lines = [l for l in text.splitlines() if re.match(r"^ {0,3}(`{3,}|~{3,})", l)]
    assert len(fence_lines) % 2 == 0, "fences must balance across the whole document"
    assert sum(1 for line in text.splitlines() if line.startswith("# ")) == 1


def test_unmatched_fence_in_an_answer_does_not_swallow_the_rest_of_the_document():
    text = _render_adversarial("before\n```python\nsome code\nno closing fence here")
    _assert_structurally_sound(text)
    sections = _sections(text)
    assert "second answer, safe and sound" in sections["v3-Q2"]
    # Q2's heading and question text must not have been absorbed into Q1's
    # (still-open, pre-fix) code block.
    assert sections["v3-Q2"].startswith("v3-Q2")


def test_leading_hash_in_an_answer_does_not_inject_a_second_top_level_heading():
    text = _render_adversarial("# Fake Top Heading\nrest of the answer")
    _assert_structurally_sound(text)
    sections = _sections(text)
    assert "second answer, safe and sound" in sections["v3-Q2"]
    # The text is preserved (escaped, not deleted).
    assert "Fake Top Heading" in text


def test_bare_dashes_in_an_answer_do_not_inject_a_rule_or_heading_break():
    text = _render_adversarial("some claim\n---\nmore text after the rule")
    _assert_structurally_sound(text)
    sections = _sections(text)
    assert "second answer, safe and sound" in sections["v3-Q2"]
    assert "more text after the rule" in sections["v3-Q1"]


def test_well_formed_fenced_code_and_tables_render_unwrapped():
    # The common case must not be degraded to defend against the rare one:
    # a well-behaved answer's code fence and table stay literal, readable
    # markdown -- not escaped, not wrapped in an outer fence.
    answer = (
        "Here is the function:\n\n"
        "```python\n"
        "def add(a, b):\n"
        "    return a + b\n"
        "```\n\n"
        "| col | val |\n"
        "| --- | --- |\n"
        "| a   | 1   |\n"
    )
    text = render_transcript(_meta(), [_q("v3-Q1", "q")], [_r("v3-Q1", answer, 5)], {})
    assert "```python\ndef add(a, b):\n    return a + b\n```" in text
    assert "| col | val |" in text
    assert "\\---" not in text  # the table's own separator row must be untouched
