"""SME review round trip.

Repo files are canonical; the spreadsheet is a transport. Export selects
questions, import writes only the verification block back, so every reviewer
verdict lands in git as a reviewable diff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from ruamel.yaml import YAML

from atlas_eval.dataset import load_bank, normalize_ws
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

# Excel format limit, not a stylistic choice: 409pt is the hard ceiling on
# row height in the XLSX file format. openpyxl will happily write a larger
# `ht` attribute, but Excel silently clamps to 409pt when the file is
# opened, which reintroduces clipping if we don't clamp first ourselves.
# A single-paragraph cell needs roughly 2400+ characters (at these column
# widths) to hit this ceiling; there is no way to show that much text in one
# visible row at any legal height. The stored value is never truncated, so
# the reviewer can still see the full text via the formula bar or by
# widening the row manually; a clamped row is a strict improvement over the
# unbounded height, which Excel would have clamped anyway while also
# clipping the last visible line.
EXCEL_MAX_ROW_HEIGHT = 409.0


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


def _style(ws, widths: tuple[int, ...]) -> None:
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
        height = min(max_lines * _LINE_HEIGHT, EXCEL_MAX_ROW_HEIGHT)
        ws.row_dimensions[row[0].row].height = height


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

    _style(review, _REVIEW_WIDTHS)
    _style(tracking, _TRACKING_WIDTHS)

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


ACCURATE_TO_STATUS: dict[str, VerificationStatus] = {
    "yes": VerificationStatus.VERIFIED,
    "no": VerificationStatus.REJECTED,
    "unsure": VerificationStatus.NEEDS_SME,
}


@dataclass
class Transition:
    question_id: str
    bank: str
    old_status: VerificationStatus
    new_status: VerificationStatus
    reviewer: str
    notes: str | None


@dataclass
class ImportReport:
    transitions: list[Transition] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unchanged: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def read_review(path: Path) -> list[dict]:
    wb = load_workbook(path, data_only=True)
    ws = wb[REVIEW_SHEET]
    headers = [c.value for c in ws[1]]
    rows: list[dict] = []
    for row in ws.iter_rows(min_row=2):
        values = [c.value for c in row]
        if all(v in (None, "") for v in values):
            continue
        rows.append({h: values[i] for i, h in enumerate(headers) if h})
    return rows


def _text(value) -> str:
    return "" if value is None else str(value).strip()


def import_review(
    path: Path,
    banks_dir: Path,
    reviewed_on: _date,
    dry_run: bool = False,
) -> ImportReport:
    """Write reviewer verdicts into bank YAML. Aborts wholesale on any error.

    Never writes ground_truth: a reviewer correction is recorded in
    verification.notes, and promoting it into ground truth is a deliberate
    separate edit made in git.
    """
    report = ImportReport()

    bank_paths = sorted(banks_dir.glob("*.yaml"))
    banks = {p: load_bank(p) for p in bank_paths}
    index: dict[str, tuple[Path, object]] = {}
    for p, bank in banks.items():
        for q in bank.questions:
            index[q.id] = (p, q)

    planned: dict[Path, dict[str, Transition]] = {}

    for row in read_review(path):
        qid = _text(row.get("id"))
        if not qid:
            continue
        if qid not in index:
            report.errors.append(
                f"{qid}: unknown question id; it is not in any bank under {banks_dir}"
            )
            continue

        bank_path, question = index[qid]

        sheet_text = _text(row.get("question"))
        if sheet_text and normalize_ws(sheet_text) != normalize_ws(question.text):
            report.errors.append(
                f"{qid}: question text in the sheet does not match the bank; an edit "
                "made in the spreadsheet must not redefine a frozen question"
            )
            continue

        verdict = _text(row.get("accurate?")).lower()
        if not verdict:
            report.unchanged += 1
            continue
        if verdict not in ACCURATE_TO_STATUS:
            report.errors.append(
                f"{qid}: 'accurate?' is {verdict!r}; expected one of "
                f"{', '.join(ACCURATE_CHOICES)}"
            )
            continue

        reviewer = _text(row.get("reviewer"))
        if not reviewer:
            report.errors.append(f"{qid}: verdict {verdict!r} has no reviewer name")
            continue

        new_status = ACCURATE_TO_STATUS[verdict]
        comments = _text(row.get("comments"))
        existing_notes = _text(row.get("notes"))
        notes = comments or existing_notes or None

        unchanged = (
            question.verification.status is new_status
            and question.verification.verified_by == reviewer
            and (question.verification.notes or "") == (notes or "")
        )
        if unchanged:
            report.unchanged += 1
            continue

        planned.setdefault(bank_path, {})[qid] = Transition(
            question_id=qid, bank=banks[bank_path].version,
            old_status=question.verification.status, new_status=new_status,
            reviewer=reviewer, notes=notes,
        )

    if report.errors:
        # Abort wholesale: a partial import leaves the corpus in a state nobody
        # reviewed, and the reviewer cannot tell which verdicts landed.
        return report

    report.transitions = [t for edits in planned.values() for t in edits.values()]
    if dry_run or not report.transitions:
        return report

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100

    for bank_path, edits in planned.items():
        with bank_path.open(encoding="utf-8") as fh:
            doc = yaml.load(fh)
        for entry in doc["questions"]:
            transition = edits.get(str(entry.get("id")))
            if transition is None:
                continue
            block = entry.get("verification")
            if block is None:
                entry["verification"] = block = {}
            block["status"] = transition.new_status.value
            block["verified_by"] = transition.reviewer
            block["verified_on"] = reviewed_on.isoformat()
            block["notes"] = transition.notes
        with bank_path.open("w", encoding="utf-8") as fh:
            yaml.dump(doc, fh)

    return report
