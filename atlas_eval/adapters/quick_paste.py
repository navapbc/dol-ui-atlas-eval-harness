"""The paste transport: the operator drives Quick, the harness parses.

This exists for two reasons. It is the documented fallback for when the UI
shifts and a run is needed before selectors are fixed, and it is the only
transport that carries no UI risk at all, which makes it the right thing to
reach for when a result matters more than automation.

Answers are delimited by an HTML comment marker, `<!-- atlas:answer
<question-id> -->`, not a markdown heading. A heading form was tried first and
rejected: the records this parses are themselves markdown, and a real Quick
answer routinely contains its own subheadings and dozens of fenced code
blocks, so a heading delimiter collides with the content it is supposed to
delimit. An incidental `### Example` subheading inside an answer would end
that answer early and swallow everything after it until the next real
heading; a fenced code sample containing a bare line that happened to match
another question's heading would split one answer and hand part of it to the
wrong question. Both are silent data corruption, not errors.

An HTML comment cannot occur in rendered markdown content by accident (it is
invisible when rendered, so nobody types one deliberately either), cannot be
confused with a heading, and survives untouched inside a fenced code block
without being misread as a delimiter, because fenced code state is tracked
explicitly below. Defence in depth on top of the delimiter change:

* A marker is only treated as a delimiter when its id is one of the questions
  actually asked. An unknown-id marker encountered while already inside an
  answer is left as ordinary content (so nothing is lost); one encountered
  before any real marker has been seen is reported as a genuinely
  unrecognised marker, so a mistyped id is not silently swallowed.
* Fenced code state (backtick or tilde fences, length three or more) is
  tracked line by line; nothing inside a fence is ever treated as a marker or
  as the `conversation:` line, regardless of what it looks like.
* The sheet's own placeholder text is a module constant shared by the writer
  and the parser, so an unfilled slot is always recognised as unanswered
  rather than stored as a real answer.
* The `conversation:` line is recognised anywhere in the document, not only
  before the first marker, and is never counted as part of any answer's body.
"""

from __future__ import annotations

import re
from datetime import datetime

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.models import Question

PLACEHOLDER = "_paste the answer here_"

_MARKER_TEMPLATE = "<!-- atlas:answer {qid} -->"

PROMPT_HEADER = """\
# Quick run sheet

Ask these in EXACTLY this order, all in the same conversation. Do not start a
new chat partway through, and do not interleave any other question: some
questions only mean something when they immediately follow the one before them.

Paste each answer back between its `<!-- atlas:answer <question-id> -->`
marker and the next one, in the Answers section below. Leave the markers
exactly as they are; only replace the placeholder text under each one.
Record the conversation id, if you have it, on the `conversation:` line at
the end (it is read wherever it appears, but the slot at the end is where it
belongs).
"""

_MARKER = re.compile(r"^\s*<!--\s*atlas:answer\s+([A-Za-z0-9._-]+)\s*-->\s*$")
_CONVERSATION = re.compile(r"^\s*conversation:\s*(\S*)\s*$", re.IGNORECASE)
_FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")


def _marker_line(question_id: str) -> str:
    return _MARKER_TEMPLATE.format(qid=question_id)


def _fence_closes(line: str, fence_char: str, fence_len: int) -> bool:
    """True if `line` is a valid closer for a fence opened with `fence_char`*`fence_len`."""
    stripped = line.strip()
    if not stripped:
        return False
    if any(ch != fence_char for ch in stripped):
        return False
    return len(stripped) >= fence_len


def render_prompt_sheet(questions: list[Question]) -> str:
    lines = [PROMPT_HEADER, "", "## Questions", ""]
    for index, question in enumerate(questions, 1):
        note = f"  _(must be asked immediately after {question.after})_" if question.after else ""
        lines += [f"## {index}. {question.id}{note}", "", question.text, ""]

    lines += ["## Answers", ""]
    for question in questions:
        lines += [_marker_line(question.id), "", PLACEHOLDER, ""]

    lines += ["conversation: ", ""]
    return "\n".join(lines)


def parse_pasted_transcript(
    text: str,
    questions: list[Question],
    asked_at: datetime,
) -> AskResult:
    """Split a pasted transcript into per-question answers.

    Returns an incomplete AskResult rather than raising, so a partial run is
    still recorded and diagnosable instead of being lost.
    """
    wanted = {q.id.lower(): q.id for q in questions}
    found: dict[str, list[str]] = {}
    unknown: list[str] = []
    conversation_id: str | None = None

    current: str | None = None
    fence_char: str | None = None
    fence_len = 0

    for line in text.splitlines():
        if fence_char is not None:
            # Inside a fenced code block: nothing here is a marker or the
            # conversation line, no matter what it looks like.
            if _fence_closes(line, fence_char, fence_len):
                fence_char = None
                fence_len = 0
            if current is not None:
                found[current].append(line)
            continue

        opening = _FENCE_OPEN.match(line)
        if opening:
            run = opening.group(1)
            fence_char = run[0]
            fence_len = len(run)
            if current is not None:
                found[current].append(line)
            continue

        marker = _MARKER.match(line)
        if marker:
            raw = marker.group(1)
            canonical = wanted.get(raw.lower())
            if canonical is not None:
                current = canonical
                found.setdefault(canonical, [])
            elif current is None:
                # A marker-shaped line with no open answer to belong to: a
                # genuine stray/mistyped id, not incidental content.
                unknown.append(raw)
            else:
                # Marker-shaped but unrecognised, and we are already inside a
                # real answer: keep it as content rather than treat it as a
                # delimiter or drop it.
                found[current].append(line)
            continue

        conversation = _CONVERSATION.match(line)
        if conversation:
            # Recognised and excluded from every answer whether or not it
            # carries a value: the sheet's own empty "conversation: " slot
            # must not bleed into whichever answer happens to precede it.
            if conversation_id is None and conversation.group(1):
                conversation_id = conversation.group(1)
            continue

        if current is not None:
            found[current].append(line)
        # else: prose outside any answer and not a marker/conversation line
        # (sheet boilerplate, blank lines) - not part of any answer.

    responses: list[Response] = []
    missing: list[str] = []
    for question in questions:  # asked order, not paste order
        body = "\n".join(found.get(question.id, [])).strip()
        if not body or body == PLACEHOLDER:
            missing.append(question.id)
            continue
        responses.append(Response(question_id=question.id, answer=body, asked_at=asked_at))

    problems: list[str] = []
    if missing:
        problems.append("no answer for: " + ", ".join(missing))
    if unknown:
        problems.append("unrecognised question id in paste: " + ", ".join(sorted(set(unknown))))

    return AskResult(
        responses=responses,
        conversation_id=conversation_id,
        complete=not problems,
        failure="; ".join(problems) or None,
    )


class QuickPasteBackend:
    """Backend whose `ask` reads an already-collected transcript."""

    name = "quick"
    transport = "paste"

    def __init__(self, agent: str, snapshot_data: dict, transcript_text: str) -> None:
        self.agent = agent
        self._snapshot = snapshot_data
        self._text = transcript_text

    def snapshot(self) -> dict:
        return self._snapshot

    def ask(self, questions: list[Question]) -> AskResult:
        return parse_pasted_transcript(self._text, questions, datetime.now())
