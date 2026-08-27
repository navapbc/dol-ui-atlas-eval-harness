"""Rubric entry: the import/export boundary for drafting rubric scores.

The harness never calls a model -- atlas_eval/scoring.py is model-free and
must stay that way. The intended process is an LLM drafts rubric scores
against the answer key outside the harness, and a human reviews them; this
module is the round trip that gets those drafted values into a run's
scores.csv (and, from there, into data/scores.csv via `atlas-eval rollup`).

Export deliberately does not carry the question text, ground truth, or the
answer into the CSV: those already live in the run's transcript.md (question
+ answer + priming context) and the bank YAML (ground truth). A second copy
in a CSV cell can drift from that record, so export prints the paths to read
instead of duplicating their content.

Import writes rubric values into the run's own scores.csv in place,
preserving ROLLUP_COLUMNS order exactly (the first 14 columns are read
positionally by an external chart) and aborts wholesale on any error --
mirroring atlas_eval/review.py's import_review. It must not go through
write_run, which now refuses to write into a non-empty run directory.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from atlas_eval.report import read_deterministic_pass
from atlas_eval.runs import ROLLUP_COLUMNS, read_run
from atlas_eval.scoring import RUBRIC_DIMENSIONS, Rubric

RUBRIC_ENTRY_COLUMNS: tuple[str, ...] = (
    "question_id", "type", "verification_status", "deterministic_pass",
    *RUBRIC_DIMENSIONS, "notes", "scored_by",
)


@dataclass
class RubricExportResult:
    exported: int
    transcript_path: Path
    bank_path: Path


def export_rubric(run_dir: Path, out_path: Path, banks_dir: Path) -> RubricExportResult:
    """Write the rubric entry CSV for one run. Returns paths the grader needs to read.

    deterministic_pass is read-only context, carried straight from the run's
    own scores.csv (read_run itself drops that detail, see its docstring).
    """
    meta, _responses, rows = read_run(run_dir)
    passes = read_deterministic_pass(run_dir)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=RUBRIC_ENTRY_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            det = passes.get(row.question_id)
            cells = {col: "" for col in RUBRIC_ENTRY_COLUMNS}
            cells.update({
                "question_id": row.question_id,
                "type": row.type,
                "verification_status": row.verification_status,
                "deterministic_pass": "" if det is None else det,
            })
            writer.writerow(cells)

    return RubricExportResult(
        exported=len(rows),
        transcript_path=run_dir / "transcript.md",
        bank_path=banks_dir / f"{meta.bank_version}.yaml",
    )


@dataclass
class RubricChange:
    question_id: str
    rubric: Rubric


@dataclass
class RubricImportReport:
    changes: list[RubricChange] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unchanged: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def _existing_rubric(rec: dict) -> Rubric:
    kwargs = {
        dim: (int(rec[dim]) if _text(rec.get(dim)) != "" else None)
        for dim in RUBRIC_DIMENSIONS
    }
    return Rubric(
        notes=_text(rec.get("notes")) or None,
        scored_by=_text(rec.get("scored_by")) or None,
        confirmed_by=_text(rec.get("confirmed_by")) or None,
        **kwargs,
    )


def import_rubric(
    csv_path: Path,
    run_dir: Path,
    scored_by: str | None = None,
    confirmed_by: str | None = None,
    dry_run: bool = False,
) -> RubricImportReport:
    """Write drafted rubric scores into the run's scores.csv. Aborts wholesale on any error.

    confirmed_by is never read from the CSV: it is only ever set from the
    `confirmed_by` parameter, applied to every row this call writes. Passing
    None leaves each row's existing confirmed_by untouched.
    """
    report = RubricImportReport()

    scores_path = run_dir / "scores.csv"
    with scores_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = tuple(reader.fieldnames or ())
        records = list(reader)
    assert fieldnames == ROLLUP_COLUMNS, (
        f"{scores_path} has unexpected columns; refusing to guess a column mapping"
    )
    by_id = {rec["question_id"]: rec for rec in records}

    with csv_path.open(newline="", encoding="utf-8") as fh:
        entry_rows = list(csv.DictReader(fh))

    planned: dict[str, Rubric] = {}
    seen_ids: set[str] = set()

    for row in entry_rows:
        qid = _text(row.get("question_id"))
        if not qid:
            continue
        if qid in seen_ids:
            report.errors.append(
                f"{qid}: duplicate id in the sheet; each question may appear at most once"
            )
            continue
        seen_ids.add(qid)
        if qid not in by_id:
            report.errors.append(
                f"{qid}: unknown question id; it is not in this run's scores.csv"
            )
            continue

        raw = {dim: _text(row.get(dim)) for dim in RUBRIC_DIMENSIONS}
        filled = {dim: v for dim, v in raw.items() if v != ""}

        invalid: list[tuple[str, str]] = []
        parsed: dict[str, int] = {}
        for dim, v in filled.items():
            try:
                n = int(v)
            except ValueError:
                invalid.append((dim, v))
                continue
            if n not in (0, 1, 2):
                invalid.append((dim, v))
            else:
                parsed[dim] = n
        if invalid:
            for dim, v in invalid:
                report.errors.append(f"{qid}: {dim} is {v!r}; expected 0, 1, or 2")
            continue

        if not filled:
            # Blank means unscored and must stay blank -- zero would mean
            # "failed this dimension", which is a different claim entirely.
            report.unchanged += 1
            continue

        if len(filled) < len(RUBRIC_DIMENSIONS):
            missing = [d for d in RUBRIC_DIMENSIONS if d not in filled]
            report.errors.append(
                f"{qid}: only {len(filled)} of 5 dimensions are scored "
                f"(missing {', '.join(missing)}); all five dimensions or none"
            )
            continue

        row_scored_by = _text(row.get("scored_by")) or scored_by
        if not row_scored_by:
            report.errors.append(
                f"{qid}: carries scores but has no scored_by (set the 'scored_by' "
                "column in the sheet or pass --scored-by)"
            )
            continue

        existing = _existing_rubric(by_id[qid])
        new_confirmed_by = confirmed_by if confirmed_by is not None else existing.confirmed_by
        notes = _text(row.get("notes")) or None

        new_rubric = Rubric(
            **parsed, notes=notes, scored_by=row_scored_by, confirmed_by=new_confirmed_by,
        )

        unchanged = (
            all(getattr(existing, d) == getattr(new_rubric, d) for d in RUBRIC_DIMENSIONS)
            and existing.notes == new_rubric.notes
            and existing.scored_by == new_rubric.scored_by
            and existing.confirmed_by == new_rubric.confirmed_by
        )
        if unchanged:
            report.unchanged += 1
            continue

        planned[qid] = new_rubric

    if report.errors:
        # Abort wholesale: a partial write leaves scores.csv in a state where
        # some rows reflect this import and others don't, with no record of
        # which, so validate everything before touching the file.
        return report

    report.changes = [RubricChange(qid, rubric) for qid, rubric in planned.items()]
    if dry_run or not report.changes:
        return report

    for qid, rubric in planned.items():
        rec = by_id[qid]
        for dim in RUBRIC_DIMENSIONS:
            rec[dim] = getattr(rubric, dim)
        rec["total"] = rubric.total
        rec["notes"] = rubric.notes or ""
        rec["scored_by"] = rubric.scored_by or ""
        rec["confirmed_by"] = rubric.confirmed_by or ""

    with scores_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec)

    return report
