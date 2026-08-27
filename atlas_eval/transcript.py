"""Render the human-readable half of a run record.

Anyone re-grading a run six months later reads this file, not the CSV. It has to
carry enough context to reinterpret a score: which agent, which model, which
conversation, and which questions were primed by the one before them.
"""

from __future__ import annotations

import re

from atlas_eval.adapters.base import Response
from atlas_eval.models import Question
from atlas_eval.runs import RunMeta, RunStatus

_MISSING = "**NO ANSWER** — the run did not capture a response for this question."

# A fenced code block opener/closer: up to 3 leading spaces, then a run of 3+
# backticks or tildes, then anything else on the line (the "info string" on an
# opening fence; a closing fence has none).
_FENCE_RE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")

# An ATX heading: up to 3 leading spaces, 1-6 '#', then a space/tab or end of
# line. ("#comment" is not a heading and must not match.)
_ATX_HEADING_RE = re.compile(r"^( {0,3})(#{1,6})(\s.*|)$")


def _rule_char(compact: str) -> str | None:
    """Return the repeated char if `compact` is a bare run of '-' or '=', else None."""
    if compact and len(set(compact)) == 1 and compact[0] in "-=":
        return compact[0]
    return None


def _sanitize_answer(answer: str) -> str:
    """Make `answer` safe to splice into the middle of a larger markdown document.

    Two independent problems, both fixed by treating each answer as its own
    self-contained unit before it is ever joined to anything else:

    1. An unmatched code fence in the answer would otherwise swallow every
       later question in the *whole* document into one code block. We track
       fence state across the answer's own lines and, if one is left open,
       append a matching closer -- so the damage (if any) is contained to
       this one answer's own text, never leaking into a sibling section.
    2. A line that happens to start with '#' (ATX heading) or is a bare run
       of '-'/'=' (thematic break / setext underline) would inject a heading
       or rule into the document's structure. We escape just the leading
       character with a backslash, which markdown renders as the literal
       character -- the visible text is unchanged, only its syntactic role
       is neutralized. This is only done for lines *outside* an open fence:
       inside a fence such lines are already inert code content, and
       escaping there would alter the literal text of the answer.
    """
    lines = answer.split("\n")
    out: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker, info = fence_match.group(2), fence_match.group(3)
            char, length = marker[0], len(marker)
            if in_fence and char == fence_char and length >= fence_len and not info.strip():
                in_fence = False
            elif not in_fence:
                in_fence, fence_char, fence_len = True, char, length
            out.append(line)
            continue

        if in_fence:
            out.append(line)
            continue

        heading_match = _ATX_HEADING_RE.match(line)
        if heading_match:
            indent, hashes, rest = heading_match.groups()
            out.append(f"{indent}\\{hashes}{rest}")
            continue

        compact = line.strip().replace(" ", "").replace("\t", "")
        rc = _rule_char(compact)
        if rc is not None:
            idx = line.index(rc)
            out.append(line[:idx] + "\\" + line[idx:])
            continue

        out.append(line)

    text = "\n".join(out)
    if in_fence:
        text += "\n" + (fence_char * fence_len)
    return text


def _render_citations(citations: list[str]) -> list[str]:
    """One bullet per citation, so a label containing a comma can't be confused
    with a citation boundary and the original list is always recoverable."""
    return ["_Citations:_", *(f"- {c}" for c in citations)]


def render_transcript(
    meta: RunMeta,
    questions: list[Question],
    responses: list[Response],
    snapshot: dict,
) -> str:
    by_id = {r.question_id: r for r in responses}

    lines: list[str] = [
        f"# {meta.run_id}",
        "",
        f"- **Backend:** {meta.backend} (transport: {meta.transport})",
        f"- **Bank:** {meta.bank_version} (`question_sha256` {meta.question_sha256[:12]}…)",
        f"- **Agent:** {meta.agent}" + (f" (`{meta.agent_id}`)" if meta.agent_id else ""),
    ]
    if meta.conversation_id:
        lines.append(f"- **Conversation:** `{meta.conversation_id}`")
    model = snapshot.get("model_chip")
    if model:
        lines.append(f"- **Model:** {model}")
    lines += [
        f"- **Started:** {meta.started_at:%Y-%m-%d %H:%M}",
        f"- **Finished:** " + (f"{meta.finished_at:%Y-%m-%d %H:%M}"
                               if meta.finished_at else "—"),
        f"- **Status:** {meta.status.value}",
        f"- **Questions asked:** {len(questions)}, answered: {len(responses)}",
        "",
    ]

    if meta.status != RunStatus.COMPLETE:
        lines += [
            "> This run is **incomplete** and is excluded from bank-level results. "
            "It is kept for diagnosis only.",
            "",
        ]

    for question in questions:
        heading = f"## {question.id}"
        if question.after:
            heading += f" (asked immediately after {question.after})"
        lines += [heading, "", f"**Q:** {question.text}", ""]

        response = by_id.get(question.id)
        if response is None:
            lines += [_MISSING, ""]
            continue

        lines += [f"**A** ({response.asked_at:%H:%M}):", "", _sanitize_answer(response.answer), ""]
        if response.citations:
            lines += [*_render_citations(response.citations), ""]

    return "\n".join(lines).rstrip() + "\n"
