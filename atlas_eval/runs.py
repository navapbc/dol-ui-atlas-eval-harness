"""The uniform run record, identical in shape across every backend.

data/scores.csv is generated from these records, never hand edited, so the flat
file cannot drift from the runs it summarises. The first fourteen columns match
the legacy scores.csv exactly so existing charts keep working; new columns
append after `notes`.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from ruamel.yaml import YAML

from atlas_eval.scoring import RUBRIC_DIMENSIONS, DeterministicScore, Rubric

_yaml = YAML(typ="rt")
_yaml.default_flow_style = False

LEGACY_COLUMNS: tuple[str, ...] = (
    "run_finished", "agent", "agent_id", "bank_version", "question_id", "type",
    "citations", "correctness", "gap_honesty", "scope_discipline", "clarity",
    "total", "conversation_id", "notes",
)

NEW_COLUMNS: tuple[str, ...] = (
    "run_id", "backend", "transport", "verification_status",
    "scored_by", "confirmed_by",
    "stance_pass", "required_all_pass", "required_any_pass", "forbidden_pass",
    "citation_recall", "deterministic_pass",
    "missing_required", "present_forbidden", "missing_citations",
)

ROLLUP_COLUMNS: tuple[str, ...] = LEGACY_COLUMNS + NEW_COLUMNS


class RunStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


class RunMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    backend: str
    transport: str
    bank_version: str
    question_sha256: str
    agent: str
    agent_id: str | None = None
    conversation_id: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    harness_git_sha: str | None = None
    status: RunStatus = RunStatus.INCOMPLETE


class ScoreRow(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    question_id: str
    type: str
    verification_status: str
    rubric: Rubric = Rubric()
    deterministic: DeterministicScore | None = None


def make_run_id(finished: datetime, backend: str, bank_version: str) -> str:
    """Match the legacy `<date>_<HHMM>` stamp used by chats/ and snapshots/."""
    return f"{finished:%Y-%m-%d_%H%M}_{backend}_{bank_version}"


def _plain(node):
    if isinstance(node, dict):
        return {str(k): _plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    return node


def _joined(values: list[str]) -> str:
    return "; ".join(values)


def _run_finished_display(run_id: str) -> str:
    """Render the `run_finished` cell from the timestamp embedded in run_id.

    run_id is stamped by make_run_id() from the run's finish time, so parsing
    it back out (rather than reformatting meta.finished_at, which is None for
    an incomplete run and need not match a run_id minted earlier) keeps this
    column populated and consistent for every run, complete or not.
    """
    date_part, time_part, _rest = run_id.split("_", 2)
    return f"{date_part} {time_part[:2]}:{time_part[2:]}"


def _row_cells(meta: RunMeta, row: ScoreRow) -> dict[str, object]:
    finished = _run_finished_display(meta.run_id)
    d = row.deterministic
    cells: dict[str, object] = {
        "run_finished": finished,
        "agent": meta.agent,
        "agent_id": meta.agent_id or "",
        "bank_version": meta.bank_version,
        "question_id": row.question_id,
        "type": row.type,
        "total": "" if row.rubric.total is None else row.rubric.total,
        "conversation_id": meta.conversation_id or "",
        "notes": row.rubric.notes or "",
        "scored_by": row.rubric.scored_by or "",
        "confirmed_by": row.rubric.confirmed_by or "",
        "run_id": meta.run_id,
        "backend": meta.backend,
        "transport": meta.transport,
        "verification_status": row.verification_status,
    }
    for dim in RUBRIC_DIMENSIONS:
        value = getattr(row.rubric, dim)
        cells[dim] = "" if value is None else value
    if d is None:
        for col in ("stance_pass", "required_all_pass", "required_any_pass",
                    "forbidden_pass", "citation_recall", "deterministic_pass",
                    "missing_required", "present_forbidden", "missing_citations"):
            cells[col] = ""
    else:
        cells.update({
            "stance_pass": "" if d.stance_pass is None else d.stance_pass,
            "required_all_pass": d.required_all_pass,
            "required_any_pass": d.required_any_pass,
            "forbidden_pass": d.forbidden_pass,
            "citation_recall": round(d.citation_recall, 4),
            "deterministic_pass": d.deterministic_pass,
            "missing_required": _joined(d.missing_required),
            "present_forbidden": _joined(d.present_forbidden),
            "missing_citations": _joined(d.missing_citations),
        })
    return cells


def _scores_csv_text(meta: RunMeta, rows: list[ScoreRow]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(_row_cells(meta, row))
    return buf.getvalue()


def write_run(
    runs_dir: Path,
    meta: RunMeta,
    responses: dict[str, str],
    transcript: str,
    snapshot: dict,
    rows: list[ScoreRow],
) -> Path:
    run_dir = runs_dir / meta.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    with (run_dir / "run.yaml").open("w", encoding="utf-8") as fh:
        _yaml.dump(json.loads(meta.model_dump_json()), fh)

    # Insertion order is the order actually asked; preserve it verbatim.
    with (run_dir / "responses.yaml").open("w", encoding="utf-8") as fh:
        _yaml.dump({"responses": [{"id": k, "answer": v} for k, v in responses.items()]}, fh)

    (run_dir / "transcript.md").write_text(transcript, encoding="utf-8")
    (run_dir / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8"
    )
    (run_dir / "scores.csv").write_text(_scores_csv_text(meta, rows), encoding="utf-8")
    return run_dir


def read_run(run_dir: Path) -> tuple[RunMeta, dict[str, str], list[ScoreRow]]:
    with (run_dir / "run.yaml").open(encoding="utf-8") as fh:
        meta = RunMeta(**_plain(_yaml.load(fh)))

    with (run_dir / "responses.yaml").open(encoding="utf-8") as fh:
        raw = _plain(_yaml.load(fh)) or {}
    responses = {item["id"]: item["answer"] for item in raw.get("responses", [])}

    rows: list[ScoreRow] = []
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            rubric_kwargs = {
                dim: (int(rec[dim]) if rec[dim] != "" else None)
                for dim in RUBRIC_DIMENSIONS
            }
            rows.append(ScoreRow(
                question_id=rec["question_id"],
                type=rec["type"],
                verification_status=rec["verification_status"],
                rubric=Rubric(
                    notes=rec["notes"] or None,
                    scored_by=rec.get("scored_by") or None,
                    confirmed_by=rec.get("confirmed_by") or None,
                    **rubric_kwargs,
                ),
                deterministic=None,
            ))
    return meta, responses, rows


def regenerate_rollup(runs_dir: Path, out_csv: Path) -> int:
    """Rewrite out_csv from every complete run. Returns the run count included."""
    records: list[tuple[str, dict[str, str]]] = []
    included = 0

    for run_dir in sorted(p for p in runs_dir.glob("*") if p.is_dir()):
        scores = run_dir / "scores.csv"
        if not (run_dir / "run.yaml").exists() or not scores.exists():
            continue
        with (run_dir / "run.yaml").open(encoding="utf-8") as fh:
            meta = RunMeta(**_plain(_yaml.load(fh)))
        if meta.status is not RunStatus.COMPLETE:
            continue
        included += 1
        with scores.open(newline="", encoding="utf-8") as fh:
            for rec in csv.DictReader(fh):
                records.append(((rec["run_finished"], rec["question_id"]), rec))

    records.sort(key=lambda pair: pair[0])
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for _, rec in records:
            writer.writerow({col: rec.get(col, "") for col in ROLLUP_COLUMNS})
    return included
