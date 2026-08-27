"""Render the human-readable half of a run record.

Anyone re-grading a run six months later reads this file, not the CSV. It has to
carry enough context to reinterpret a score: which agent, which model, which
conversation, and which questions were primed by the one before them.
"""

from __future__ import annotations

from atlas_eval.adapters.base import Response
from atlas_eval.models import Question
from atlas_eval.runs import RunMeta

_MISSING = "**NO ANSWER** — the run did not capture a response for this question."


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

    if meta.status.value != "complete":
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

        lines += [f"**A** ({response.asked_at:%H:%M}):", "", response.answer, ""]
        if response.citations:
            lines += ["_Citations: " + ", ".join(response.citations) + "_", ""]

    return "\n".join(lines).rstrip() + "\n"
