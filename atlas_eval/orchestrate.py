"""Wire a backend to the scorer and the run record.

This is the layer that makes backends comparable: whichever transport ran, the
questions are asked in the same resolved order, scored by the same deterministic
rules, and written to the same five-file record.

It never writes a rubric value. Rubric scoring is the audit process's job (an
LLM drafts, a human confirms), and those columns stay blank here so a zero is
never confused with "nobody has scored this".
"""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

from atlas_eval.dataset import compute_question_sha256, load_bank, resolve_run_order
from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, make_run_id, write_run
from atlas_eval.scoring import Rubric, score_answer
from atlas_eval.transcript import render_transcript


class OrchestrationError(Exception):
    """The run could not be started."""


def _git_sha() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=False)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except OSError:
        return None


def run_bank(
    bank_path: Path,
    backend,
    runs_dir: Path,
    scored_by: str = "harness-deterministic",
    harness_git_sha: str | None = None,
    now: datetime | None = None,
) -> Path:
    bank = load_bank(bank_path)

    # Refuse before asking anything: a frozen bank whose questions changed would
    # produce scores that silently refer to questions that no longer exist.
    actual = compute_question_sha256(bank)
    if bank.frozen_on is not None:
        if not bank.question_sha256:
            raise OrchestrationError(
                f"{bank_path} is frozen ({bank.frozen_on}) but has no question_sha256"
            )
        if bank.question_sha256 != actual:
            raise OrchestrationError(
                f"{bank_path}: question_sha256 mismatch (recorded "
                f"{bank.question_sha256[:12]}, actual {actual[:12]}). A frozen "
                "question's id or text changed; bump the bank version instead of "
                "running against it."
            )

    questions = resolve_run_order(bank)
    started = now or datetime.now()

    result = backend.ask(questions)
    snapshot = backend.snapshot()
    finished = now or datetime.now()

    by_id = {r.question_id: r for r in result.responses}
    rows: list[ScoreRow] = []
    for question in questions:
        response = by_id.get(question.id)
        if response is None:
            continue
        rows.append(ScoreRow(
            question_id=question.id,
            type=question.type.value,
            verification_status=question.verification.status.value,
            rubric=Rubric(scored_by=scored_by),
            deterministic=score_answer(question, response.answer,
                                       response.observed_stance),
        ))

    status = RunStatus.COMPLETE if result.complete else RunStatus.INCOMPLETE
    meta = RunMeta(
        run_id=make_run_id(finished, backend.name, bank.version),
        backend=backend.name,
        transport=backend.transport,
        bank_version=bank.version,
        question_sha256=bank.question_sha256 or actual,
        agent=bank.agent,
        agent_id=(snapshot.get("agent") or {}).get("AgentId"),
        conversation_id=result.conversation_id,
        started_at=started,
        finished_at=finished if result.complete else None,
        harness_git_sha=harness_git_sha or _git_sha(),
        status=status,
    )

    transcript = render_transcript(meta, questions, result.responses, snapshot)
    if result.failure:
        transcript += f"\n---\n\n**Run failure:** {result.failure}\n"

    return write_run(
        runs_dir, meta,
        {r.question_id: r.answer for r in result.responses},
        transcript, snapshot, rows,
    )
