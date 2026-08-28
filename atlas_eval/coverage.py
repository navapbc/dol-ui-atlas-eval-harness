"""Verification progress across the banks.

Verification is the harness's only gate on a defensible number: a run's
headline score counts verified questions and nothing else. When several SMEs
review asynchronously, partial coverage is the steady state for weeks -- and
in the run report, "nobody has started" and "reviewed but nothing held up"
both render as `verified deterministic n/a`. They are not the same thing, so
progress needs its own view.

This module only reads the banks. It never scores, never writes, and has no
opinion about which questions belong to which reviewer: the harness records
verdicts, not assignments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from atlas_eval.dataset import load_all_banks
from atlas_eval.models import Bank, VerificationStatus

# Column order for every tally table. `unverified` last so the eye lands on
# the work remaining.
_STATUSES: tuple[VerificationStatus, ...] = (
    VerificationStatus.VERIFIED,
    VerificationStatus.REJECTED,
    VerificationStatus.NEEDS_SME,
    VerificationStatus.UNVERIFIED,
)

_NO_REVIEWER = "(unattributed)"

_WS = re.compile(r"\s+")


def _squeeze(text: str | None) -> str:
    """Collapse whitespace but preserve case.

    dataset.normalize_ws lowercases, which is right for matching and wrong
    for display: a reviewer's name is shown back to them.
    """
    return _WS.sub(" ", text or "").strip()


@dataclass
class Tally:
    """Question counts by verification status."""

    counts: dict[VerificationStatus, int] = field(
        default_factory=lambda: {s: 0 for s in _STATUSES}
    )

    def add(self, status: VerificationStatus) -> None:
        self.counts[status] = self.counts.get(status, 0) + 1

    def __getitem__(self, status: VerificationStatus) -> int:
        return self.counts.get(status, 0)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def reviewed(self) -> int:
        """Questions carrying any verdict at all.

        A `rejected` or `needs-sme` question is SME attention already spent,
        so it counts as progress even though it will never feed a score.
        """
        return self.total - self[VerificationStatus.UNVERIFIED]

    @property
    def reviewed_pct(self) -> float:
        return 0.0 if not self.total else 100.0 * self.reviewed / self.total

    @property
    def verified_pct(self) -> float:
        return (
            0.0 if not self.total
            else 100.0 * self[VerificationStatus.VERIFIED] / self.total
        )


@dataclass
class BankCoverage:
    version: str
    frozen_on: str
    tally: Tally


@dataclass
class ReviewerCoverage:
    """One reviewer's verdicts. `name` is the display spelling."""

    name: str
    tally: Tally
    variants: list[str] = field(default_factory=list)


@dataclass
class QuestionCoverage:
    id: str
    bank: str
    status: VerificationStatus
    reviewer: str
    verified_on: str
    note: str


@dataclass
class Coverage:
    banks_dir: Path
    questions: list[QuestionCoverage]
    banks: list[BankCoverage]
    reviewers: list[ReviewerCoverage]
    overall: Tally
    needs_sme: list[tuple[str, str]]
    undated: list[str]


def _reviewer_key(raw: str | None) -> str:
    return _squeeze(raw).casefold()


def build_coverage(banks_dir: Path) -> Coverage:
    banks: list[Bank] = load_all_banks(banks_dir)

    overall = Tally()
    per_bank: list[BankCoverage] = []
    # Grouped case- and whitespace-insensitively: several SMEs typing their own
    # names into a spreadsheet will not spell them identically, and splitting
    # "Oscar" from "oscar" would understate both.
    by_reviewer: dict[str, tuple[Tally, list[str]]] = {}
    needs_sme: list[tuple[str, str]] = []
    undated: list[str] = []
    questions: list[QuestionCoverage] = []

    for bank in banks:
        tally = Tally()
        for q in bank.questions:
            status = q.verification.status
            tally.add(status)
            overall.add(status)

            reviewer = _squeeze(q.verification.verified_by)
            questions.append(
                QuestionCoverage(
                    id=q.id,
                    bank=bank.version,
                    status=status,
                    reviewer=reviewer,
                    verified_on=(
                        "" if q.verification.verified_on is None
                        else str(q.verification.verified_on)
                    ),
                    note=_squeeze(q.verification.notes),
                )
            )

            if status is VerificationStatus.NEEDS_SME:
                needs_sme.append((q.id, _squeeze(q.verification.notes)))

            if status is VerificationStatus.UNVERIFIED:
                continue

            display = _squeeze(q.verification.verified_by) or _NO_REVIEWER
            key = _reviewer_key(q.verification.verified_by) or _NO_REVIEWER
            slot = by_reviewer.setdefault(key, (Tally(), []))
            slot[0].add(status)
            if display not in slot[1]:
                slot[1].append(display)

            if q.verification.verified_on is None:
                undated.append(q.id)

        per_bank.append(
            BankCoverage(
                version=bank.version,
                frozen_on="" if bank.frozen_on is None else str(bank.frozen_on),
                tally=tally,
            )
        )

    reviewers = [
        ReviewerCoverage(name=spellings[0], tally=tally, variants=spellings[1:])
        # Most verdicts first, then by name, so the table reads as a leaderboard
        # of who has actually returned work.
        for _key, (tally, spellings) in sorted(
            by_reviewer.items(), key=lambda kv: (-kv[1][0].total, kv[0])
        )
    ]

    return Coverage(
        banks_dir=banks_dir,
        questions=questions,
        banks=per_bank,
        reviewers=reviewers,
        overall=overall,
        needs_sme=needs_sme,
        undated=undated,
    )


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    """Render a fixed-width table. Column 0 left-aligned, the rest right."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells: list[str]) -> str:
        out = [cells[0].ljust(widths[0])]
        out += [c.rjust(widths[i]) for i, c in enumerate(cells[1:], start=1)]
        return "  ".join(out).rstrip()

    return [fmt(headers)] + [fmt(r) for r in rows]


def _tally_cells(tally: Tally) -> list[str]:
    return [str(tally.total)] + [str(tally[s]) for s in _STATUSES] + [
        f"{tally.reviewed_pct:.0f}%"
    ]


_TALLY_HEADERS = ["total", "verified", "rejected", "needs-sme", "unverified", "reviewed"]


def format_coverage(cov: Coverage, detail: bool = False) -> str:
    lines: list[str] = [f"verification coverage -- {cov.banks_dir}", ""]

    if not cov.overall.total:
        lines.append(f"no questions found in {cov.banks_dir}")
        return "\n".join(lines)

    rows = [
        [b.version] + _tally_cells(b.tally) + [b.frozen_on or "(held out)"]
        for b in cov.banks
    ]
    rows.append(["all"] + _tally_cells(cov.overall) + [""])
    lines += _table(["bank"] + _TALLY_HEADERS + ["frozen"], rows)
    lines.append("")

    if cov.reviewers:
        rrows = []
        for r in cov.reviewers:
            label = r.name
            if r.variants:
                label += " (also: " + ", ".join(r.variants) + ")"
            rrows.append(
                [label, str(r.tally.total)]
                + [str(r.tally[s]) for s in _STATUSES[:-1]]
            )
        lines += _table(
            ["reviewer", "verdicts", "verified", "rejected", "needs-sme"], rrows
        )
        lines.append("")
    else:
        lines += ["reviewers: none yet -- no verdict has been imported.", ""]

    verified = cov.overall[VerificationStatus.VERIFIED]
    if not verified:
        lines.append(
            "Nothing is verified, so every run reports `verified deterministic "
            "n/a`.\nThat number stays n/a until the first `accurate? = yes` "
            "verdict is imported."
        )
    else:
        lines.append(
            f"{verified} of {cov.overall.total} question(s) "
            f"({cov.overall.verified_pct:.0f}%) can feed a verified score."
        )

    if cov.needs_sme:
        lines += ["", f"awaiting a different SME ({len(cov.needs_sme)}):"]
        for qid, note in cov.needs_sme:
            suffix = f" -- {note}" if note else ""
            lines.append(f"  {qid}{suffix}")

    if cov.undated:
        lines += [
            "",
            f"verdict recorded with no date ({len(cov.undated)}): "
            + ", ".join(cov.undated),
        ]

    if detail:
        # Flat and one question per line, so the listing can be grepped and
        # pasted straight into a status note.
        lines += ["", "per question:"]
        lines += _table(
            ["question", "bank", "status", "reviewer", "on", "note"],
            [
                [
                    q.id,
                    q.bank,
                    q.status.value,
                    q.reviewer or "-",
                    q.verified_on or "-",
                    q.note or "-",
                ]
                for q in cov.questions
            ],
        )

    return "\n".join(lines)
