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

from atlas_eval.adapters.base import Response
from atlas_eval.dataset import compute_question_sha256, load_bank, resolve_run_order
from atlas_eval.models import Question
from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, make_run_id, write_run
from atlas_eval.scoring import Rubric, score_answer
from atlas_eval.transcript import render_transcript


class OrchestrationError(Exception):
    """The run could not be started."""


def _git_sha() -> str | None:
    """The commit the harness is running from, or None if it can't be determined.

    Suffixed with "-dirty" when the working tree has uncommitted changes: a sha
    with no such marker is supposed to fully describe the code that produced a
    run, and this harness exists so a score from months ago can be
    reinterpreted against that code. A bare sha recorded from a dirty tree
    would be silently misleading, so the marker makes "this run's code isn't
    fully captured by this sha" visible instead of assumed away.

    Must never raise: degrades to None when git is unavailable (OSError, e.g.
    the binary isn't installed) or the directory is not a repository (`git
    rev-parse` exits non-zero).
    """
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=False)
        if rev.returncode != 0:
            return None
        sha = rev.stdout.strip()
        if not sha:
            return None

        status = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                                 text=True, check=False)
        if status.returncode == 0 and status.stdout.strip():
            return f"{sha}-dirty"
        return sha
    except OSError:
        return None


def _validate_responses(
    questions: list[Question], responses: list[Response]
) -> tuple[list[Response], list[str]]:
    """Sanitize a backend's responses before they touch the run record.

    A misbehaving backend can return two kinds of data nobody asked for: the
    same question_id twice (the second silently displaces the first wherever
    responses are keyed by id, so the real answer disappears with no trace),
    or a question_id that was never asked (which would otherwise be written
    into responses.yaml as though it had been). Both are detected here and
    both are stripped out entirely -- for a duplicate, neither copy can be
    trusted to be the "real" one, so both are dropped rather than guessing.

    Returns the sanitized response list (safe to write and to score) and a
    list of human-readable problem descriptions naming the offending id(s),
    empty when nothing was wrong.
    """
    asked_ids = {q.id for q in questions}
    counts: dict[str, int] = {}
    for response in responses:
        counts[response.question_id] = counts.get(response.question_id, 0) + 1

    duplicate_ids = sorted(qid for qid, n in counts.items() if n > 1)
    stray_ids = sorted(qid for qid in counts if qid not in asked_ids)

    problems = []
    if duplicate_ids:
        problems.append(
            "backend returned a duplicate response for question_id(s): "
            + ", ".join(duplicate_ids)
        )
    if stray_ids:
        problems.append(
            "backend returned response(s) for question_id(s) not among the "
            "questions asked: " + ", ".join(stray_ids)
        )

    tainted = set(duplicate_ids) | set(stray_ids)
    clean = [r for r in responses if r.question_id not in tainted]
    return clean, problems


def load_and_check_bank(bank_path: Path):
    """Load a bank and refuse it before anything else happens, if it is frozen
    and its questions have since changed.

    Split out of run_bank so a caller that is about to do something
    irreversible or costly first -- opening a headed browser, hitting a live
    URL -- can run this exact check before doing that, rather than finding
    out only after run_bank gets around to it. Returns the loaded Bank so a
    caller like the CLI's playwright path doesn't have to load it a second
    time by hand; run_bank still calls this itself so every caller, not just
    ones that remembered to check first, is protected.
    """
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
    return bank


def run_bank(
    bank_path: Path,
    backend,
    runs_dir: Path,
    scored_by: str = "harness-deterministic",
    harness_git_sha: str | None = None,
    now: datetime | None = None,
) -> Path:
    bank = load_and_check_bank(bank_path)
    actual = compute_question_sha256(bank)

    questions = resolve_run_order(bank)
    started = now or datetime.now()

    result = backend.ask(questions)
    snapshot = backend.snapshot()
    finished = now or datetime.now()

    # The backend has already run by this point, so the work is done; the
    # question is only what we do with a response set we cannot trust. We
    # write the run as `incomplete` (rather than raising and discarding the
    # work) because that status already means exactly this: kept on disk for
    # diagnosis, excluded from bank-level results. Raising here would throw
    # away the started_at/snapshot/backend-name evidence an operator needs to
    # even notice which run and which backend misbehaved.
    clean_responses, problems = _validate_responses(questions, result.responses)

    by_id = {r.question_id: r for r in clean_responses}
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

    failure = result.failure
    if problems:
        problem_text = "; ".join(problems)
        failure = f"{failure}; {problem_text}" if failure else problem_text

    status = RunStatus.COMPLETE if (result.complete and not problems) else RunStatus.INCOMPLETE
    meta = RunMeta(
        run_id=make_run_id(finished, backend.name, backend.transport, bank.version),
        backend=backend.name,
        transport=backend.transport,
        bank_version=bank.version,
        question_sha256=bank.question_sha256 or actual,
        agent=bank.agent,
        agent_id=(snapshot.get("agent") or {}).get("AgentId"),
        conversation_id=result.conversation_id,
        started_at=started,
        finished_at=finished if status == RunStatus.COMPLETE else None,
        harness_git_sha=harness_git_sha or _git_sha(),
        status=status,
    )

    transcript = render_transcript(meta, questions, clean_responses, snapshot)
    if failure:
        transcript += f"\n---\n\n**Run failure:** {failure}\n"

    try:
        return write_run(
            runs_dir, meta,
            {r.question_id: r.answer for r in clean_responses},
            transcript, snapshot, rows,
        )
    except FileExistsError as err:
        # A collision here means make_run_id's inputs (finished-minute,
        # backend, transport, bank_version) really did repeat -- surface it
        # as an OrchestrationError, same as any other reason a run couldn't
        # be started, rather than a raw traceback out of run_bank.
        raise OrchestrationError(str(err)) from err
