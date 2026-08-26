"""SME review round trip.

Repo files are canonical; the spreadsheet is a transport. Export selects
questions, import writes only the verification block back, so every reviewer
verdict lands in git as a reviewable diff.
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from atlas_eval.models import Bank, Question, VerificationStatus

REVIEW_SHEET = "Review"
TRACKING_SHEET = "Our tracking"

REVIEW_COLUMNS: tuple[str, ...] = (
    "id", "question", "type", "expected answer", "notes", "accurate?", "reviewer",
    "comments",
)

TRACKING_COLUMNS: tuple[str, ...] = (
    "id", "bank", "type_note", "provenance", "required_all", "required_any",
    "forbidden", "expect_citations", "current status", "expected stance",
)

ACCURATE_CHOICES: tuple[str, ...] = ("yes", "no", "unsure")

# accurate? <-> verification status. Import reverses this mapping.
STATUS_TO_ACCURATE: dict[VerificationStatus, str] = {
    VerificationStatus.VERIFIED: "yes",
    VerificationStatus.REJECTED: "no",
    VerificationStatus.NEEDS_SME: "unsure",
    VerificationStatus.UNVERIFIED: "",
}

_REVIEW_WIDTHS = (12, 60, 18, 90, 40, 11, 14, 40)
_TRACKING_WIDTHS = (12, 8, 26, 34, 26, 26, 22, 30, 15, 16)

_LINE_HEIGHT = 15.0  # points; openpyxl/Excel's default single-line row height.


def _joined(values: list[str]) -> str:
    return "; ".join(values)


def _wrapped_lines(text: str, width: int) -> int:
    """Estimate how many wrapped display lines `text` needs at column `width`.

    openpyxl never sets a row's height for us, and Excel does not reliably
    auto-fit row height for wrap_text cells it did not itself lay out: a
    long ground-truth cell (some run past 1800 characters here) would
    otherwise render as a single clipped line even though wrap_text is on.
    Each explicit newline starts a fresh wrapped paragraph, matching how
    Excel itself wraps multi-line cell content.
    """
    if not text:
        return 1
    chars_per_line = max(width - 2, 10)
    return sum(max(1, -(-len(p) // chars_per_line)) for p in text.split("\n"))


def _review_row(q: Question) -> list[str]:
    return [
        q.id,
        q.text,
        q.type.value,
        q.ground_truth.strip(),
        (q.verification.notes or "").strip(),
        STATUS_TO_ACCURATE[q.verification.status],
        q.verification.verified_by or "",
        "",
    ]


def _tracking_row(bank: Bank, q: Question) -> list[str]:
    return [
        q.id, bank.version, q.type_note or "", q.provenance or "",
        _joined(q.checks.required_all), _joined(q.checks.required_any),
        _joined(q.checks.forbidden), _joined(q.checks.expect_citations),
        q.verification.status.value, q.expected_stance.value,
    ]


def _style(ws, columns: tuple[str, ...], widths: tuple[int, ...]) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "A2"
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    for row in ws.iter_rows(min_row=2):
        max_lines = 1
        for cell, width in zip(row, widths):
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.value:
                max_lines = max(max_lines, _wrapped_lines(str(cell.value), width))
        ws.row_dimensions[row[0].row].height = max_lines * _LINE_HEIGHT


def export_review(
    banks: list[Bank],
    out_path: Path,
    statuses: set[VerificationStatus] | None = None,
) -> int:
    """Write the review workbook. Returns the number of questions exported."""
    wb = Workbook()
    review = wb.active
    review.title = REVIEW_SHEET
    review.append(list(REVIEW_COLUMNS))
    tracking = wb.create_sheet(TRACKING_SHEET)
    tracking.append(list(TRACKING_COLUMNS))

    exported = 0
    for bank in banks:
        for q in bank.questions:
            if statuses is not None and q.verification.status not in statuses:
                continue
            review.append(_review_row(q))
            tracking.append(_tracking_row(bank, q))
            exported += 1

    _style(review, REVIEW_COLUMNS, _REVIEW_WIDTHS)
    _style(tracking, TRACKING_COLUMNS, _TRACKING_WIDTHS)

    if exported:
        col = get_column_letter(REVIEW_COLUMNS.index("accurate?") + 1)
        dv = DataValidation(
            type="list", formula1=f'"{",".join(ACCURATE_CHOICES)}"', allow_blank=True,
            showErrorMessage=True, error="Choose yes, no, or unsure.",
        )
        review.add_data_validation(dv)
        dv.add(f"{col}2:{col}{exported + 1}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return exported
