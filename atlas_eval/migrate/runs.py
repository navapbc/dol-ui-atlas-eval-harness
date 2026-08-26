"""Rebuild run records from the legacy scores.csv, chats/ and snapshots/.

Read-only with respect to the source tree. Legacy runs carry transport
"legacy": they were driven by hand, and their transcripts were never split
into per-question responses, so responses.yaml is empty rather than guessed.
"""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path

from atlas_eval.runs import RunMeta, RunStatus, ScoreRow, write_run
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric

_STAMP = re.compile(r"^(\d{4}-\d{2}-\d{2}) (\d{2}):(\d{2})$")
AGENT_SLUG = "engineering_onboarding_specialist"

# Explicit stamp -> stamp overrides for a transcript that documents more than
# one scored run. Evidence (2026-08-26 investigation, see task-11 brief):
# chats/2026-08-12_1527_engineering_onboarding_specialist.md's own header
# reads "Runs: v1 full (conv 1f352d59, 3:02-3:11), v2 full (conv 7e143e0e,
# 3:13-3:23), v5-Q4 spot, v3-Q1 spot" -- a single sitting that covered two
# full scored runs plus spot checks. The scores.csv rows stamped 2026-08-12
# 15:11/v1 and 2026-08-12 15:23/v2 have no transcript of their own, and their
# conversation_id values ("1f352d59-regression" and "7e143e0e-regression")
# match that header exactly, corroborating the same-sitting claim. This is
# the only legacy stamp verified to span multiple conversations -- every
# other stamp maps 1:1 to its own chat/snapshot files -- so this stays a
# small, hand-verified, two-entry mapping rather than fuzzy timestamp
# matching. Do not extend it without the same kind of corroborating evidence.
SHARED_TRANSCRIPT_STAMPS: dict[str, str] = {
    "2026-08-12_1511": "2026-08-12_1527",
    "2026-08-12_1523": "2026-08-12_1527",
}


def stamp_from_run_finished(value: str) -> str:
    m = _STAMP.match(value.strip())
    if not m:
        raise ValueError(f"unexpected run_finished format: {value!r}")
    return f"{m.group(1)}_{m.group(2)}{m.group(3)}"


def group_legacy_scores(rows: list[dict]) -> dict[tuple[str, str], list[dict]]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in rows:
        groups.setdefault((rec["run_finished"], rec["bank_version"]), []).append(rec)
    return groups


def legacy_row_to_score_row(
    rec: dict,
    scored_by: str = "legacy-audit",
    confirmed_by: str | None = None,
) -> ScoreRow:
    def cell(name: str) -> int | None:
        raw = (rec.get(name) or "").strip()
        return int(raw) if raw else None

    return ScoreRow(
        question_id=rec["question_id"],
        type=rec["type"],
        verification_status="unverified",
        rubric=Rubric(
            notes=(rec.get("notes") or "").strip() or None,
            scored_by=scored_by,
            confirmed_by=confirmed_by,
            **{dim: cell(dim) for dim in RUBRIC_DIMENSIONS},
        ),
        deterministic=None,
    )


def _load_snapshot(snapshots: Path, stamp: str) -> dict:
    """Merge the agent and spaces snapshots for one run stamp."""
    merged: dict = {}
    agent_file = snapshots / f"{stamp}_{AGENT_SLUG}.json"
    spaces_file = snapshots / f"{stamp}_spaces.json"
    if agent_file.exists():
        merged["agent"] = json.loads(agent_file.read_text(encoding="utf-8"))
    if spaces_file.exists():
        merged["spaces"] = json.loads(spaces_file.read_text(encoding="utf-8"))
    return merged


def _annotate_shared_transcript(run_dir: Path, stamp: str, source_stamp: str) -> None:
    """Append a comment to run.yaml documenting a borrowed transcript/snapshot.

    RunMeta forbids extra fields (see atlas_eval/runs.py), so this is a plain
    trailing YAML comment rather than a model field: read_run's round-trip
    load ignores it, but a human reading run.yaml sees exactly where the
    transcript and snapshot came from.
    """
    note = (
        f"# NOTE: transcript.md and snapshot.json for this run were borrowed from\n"
        f"# stamp {source_stamp} (chats/{source_stamp}_{AGENT_SLUG}.md), which documents\n"
        f"# multiple scored runs from one sitting. See SHARED_TRANSCRIPT_STAMPS in\n"
        f"# atlas_eval/migrate/runs.py for the evidence. This run's own stamp is {stamp}.\n"
    )
    with (run_dir / "run.yaml").open("a", encoding="utf-8") as fh:
        fh.write(note)


def migrate_runs(
    source: Path,
    runs_dir: Path,
    scored_by: str = "legacy-audit",
    confirmed_by: str | None = None,
) -> list[str]:
    with (source / "scores.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    written: list[str] = []
    for (finished, version), group in sorted(group_legacy_scores(rows).items()):
        stamp = stamp_from_run_finished(finished)
        source_stamp = SHARED_TRANSCRIPT_STAMPS.get(stamp, stamp)
        first = group[0]
        when = datetime.strptime(finished, "%Y-%m-%d %H:%M")
        run_id = f"{stamp}_quick_{version}"

        chat = source / "chats" / f"{source_stamp}_{AGENT_SLUG}.md"
        transcript = (
            chat.read_text(encoding="utf-8") if chat.exists()
            else f"<!-- no transcript found for {stamp} in the legacy chats/ directory -->\n"
        )

        meta = RunMeta(
            run_id=run_id,
            backend="quick",
            transport="legacy",
            bank_version=version,
            # Legacy runs predate freeze hashing; recorded as unknown rather than
            # back-computed, since the bank text may have moved since.
            question_sha256="legacy-unknown",
            agent=first["agent"],
            agent_id=(first.get("agent_id") or "").strip() or None,
            conversation_id=(first.get("conversation_id") or "").strip() or None,
            started_at=when,
            finished_at=when,
            harness_git_sha=None,
            status=RunStatus.COMPLETE,
        )

        run_dir = write_run(
            runs_dir, meta,
            responses={},
            transcript=transcript,
            snapshot=_load_snapshot(source / "snapshots", source_stamp),
            rows=[legacy_row_to_score_row(rec, scored_by, confirmed_by)
                  for rec in group],
        )
        if source_stamp != stamp:
            _annotate_shared_transcript(run_dir, stamp, source_stamp)
        written.append(run_id)

    return written
