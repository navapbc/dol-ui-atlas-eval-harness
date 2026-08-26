"""Reporting that keeps the defensible number separate from the exploratory one.

The banks were built with AI assistance and are verified incrementally, so a
run normally covers a partly verified bank. Merging the two figures would
present unvetted ground truth as though an SME had signed off on it, so they
are computed and printed separately, always.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from atlas_eval.dataset import load_all_banks
from atlas_eval.models import VerificationStatus
from atlas_eval.runs import RunStatus, read_run
from atlas_eval.scoring import RUBRIC_DIMENSIONS


@dataclass
class Subset:
    label: str
    question_count: int
    deterministic_pass: int
    rubric_total: int | None
    rubric_max: int | None
    confirmed_count: int


@dataclass
class RunReport:
    run_id: str
    bank_version: str
    backend: str
    status: RunStatus
    verified: Subset
    exploratory: Subset


def _read_deterministic_pass(run_dir: Path) -> dict[str, bool | None]:
    """scores.csv is the record; read the deterministic column back verbatim."""
    out: dict[str, bool | None] = {}
    with (run_dir / "scores.csv").open(newline="", encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            raw = (rec.get("deterministic_pass") or "").strip()
            out[rec["question_id"]] = None if raw == "" else raw == "True"
    return out


def _subset(label: str, rows, passes: dict[str, bool | None]) -> Subset:
    scored = [r for r in rows if r.rubric.total is not None]
    return Subset(
        label=label,
        question_count=len(rows),
        deterministic_pass=sum(1 for r in rows if passes.get(r.question_id) is True),
        rubric_total=sum(r.rubric.total for r in scored) if scored else None,
        rubric_max=len(scored) * 2 * len(RUBRIC_DIMENSIONS) if scored else None,
        confirmed_count=sum(1 for r in rows if r.rubric.is_confirmed),
    )


def build_report(run_dir: Path, banks_dir: Path) -> RunReport:
    meta, _responses, rows = read_run(run_dir)
    if meta.status is not RunStatus.COMPLETE:
        raise ValueError(
            f"{meta.run_id} is {meta.status.value}; an incomplete run cannot be "
            "reported as a bank result"
        )

    bank = next((b for b in load_all_banks(banks_dir) if b.version == meta.bank_version), None)
    if bank is None:
        raise ValueError(f"no bank {meta.bank_version} under {banks_dir}")

    status_by_id = {q.id: q.verification.status for q in bank.questions}
    passes = _read_deterministic_pass(run_dir)

    verified_rows = [
        r for r in rows if status_by_id.get(r.question_id) is VerificationStatus.VERIFIED
    ]

    return RunReport(
        run_id=meta.run_id,
        bank_version=meta.bank_version,
        backend=meta.backend,
        status=meta.status,
        verified=_subset("verified", verified_rows, passes),
        exploratory=_subset("exploratory (unvetted)", rows, passes),
    )


def _line(s: Subset) -> str:
    rubric = (
        "rubric n/a" if s.rubric_total is None
        else f"rubric {s.rubric_total}/{s.rubric_max}"
    )
    return (f"  {s.label:<24} deterministic {s.deterministic_pass}/{s.question_count}"
            f"   {rubric}   human-confirmed {s.confirmed_count}/{s.question_count}")


def format_report(report: RunReport) -> str:
    lines = [
        f"{report.run_id}  ({report.backend}, bank {report.bank_version})",
        _line(report.verified),
        _line(report.exploratory),
    ]
    if report.verified.question_count == 0:
        lines.append(
            "  NOTE: no verified questions in this bank yet, so there is no "
            "defensible figure. Treat the exploratory number as unvetted."
        )
    return "\n".join(lines)
