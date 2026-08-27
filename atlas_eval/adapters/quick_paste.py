"""The paste transport: the operator drives Quick, the harness parses.

This exists for two reasons. It is the documented fallback for when the UI
shifts and a run is needed before selectors are fixed, and it is the only
transport that carries no UI risk at all, which makes it the right thing to
reach for when a result matters more than automation.

Answers are delimited by `### <question-id>`, the same heading form the existing
answer-key notes use.
"""

from __future__ import annotations

import re
from datetime import datetime

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.models import Question

PROMPT_HEADER = """\
# Quick run sheet

Ask these in EXACTLY this order, all in the same conversation. Do not start a
new chat partway through, and do not interleave any other question: some
questions only mean something when they immediately follow the one before them.

Paste each answer back under a heading of the form `### <question-id>`, and
optionally record the conversation id on a line reading `conversation: <id>`.
"""

_HEADING = re.compile(r"^\s*###\s*([A-Za-z0-9._-]+)\s*$")
_CONVERSATION = re.compile(r"^\s*conversation:\s*(\S+)\s*$", re.IGNORECASE)


def render_prompt_sheet(questions: list[Question]) -> str:
    lines = [PROMPT_HEADER, ""]
    for index, question in enumerate(questions, 1):
        note = f"  _(must be asked immediately after {question.after})_" if question.after else ""
        lines += [f"## {index}. {question.id}{note}", "", question.text, "",
                  f"### {question.id}", "", "_paste the answer here_", ""]
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
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            raw = heading.group(1)
            canonical = wanted.get(raw.lower())
            if canonical is None:
                unknown.append(raw)
                current = None
            else:
                current = canonical
                found.setdefault(canonical, [])
            continue
        if current is None:
            conversation = _CONVERSATION.match(line)
            if conversation and conversation_id is None:
                conversation_id = conversation.group(1)
            continue
        found[current].append(line)

    responses: list[Response] = []
    missing: list[str] = []
    for question in questions:  # asked order, not paste order
        body = "\n".join(found.get(question.id, [])).strip()
        if not body:
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
