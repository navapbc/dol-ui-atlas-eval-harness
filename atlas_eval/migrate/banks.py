"""Parse the legacy Markdown bank and answer keys into Bank models."""

from __future__ import annotations

import re

from atlas_eval.migrate.type_map import map_legacy_type
from atlas_eval.models import Bank, Checks, Question, QuestionType, Stance

_VERSION_H2 = re.compile(r"^##\s+(v\d+)\s*\(", re.MULTILINE)
_ROW = re.compile(r"^\|\s*(v\d+-Q\d+)\s*\|(.+?)\|(.+?)\|(.+?)\|\s*$", re.MULTILINE)

# Matches a Markdown ## or ### heading line. Question ground truth always
# lives in a ### block, but which ## section wraps it varies (some answer
# keys have no wrapping "## Ground truth per question" heading at all — see
# v5_answer_key.md), so headings are found generically rather than by
# anchoring on that one heading's text.
_HEADING = re.compile(r"^(#{2,3})[ \t]+(.*?)[ \t]*$", re.MULTILINE)
_QID = re.compile(r"^(v\d+-Q\d+)\b")

_REFUSE_CUES = ("must refuse", "must say not found", "should decline", "not available",
                "no such document", "must not invent")
_HEDGE_CUES = ("should hedge", "needs sme confirmation", "flags kb scope",
               "must not invent a code list", "honest that")
_REDIRECT_CUES = ("maps it to", "premise correction", "redirect")

# Default stance per mapped question type, used only when no explicit
# behaviour cue above already decided it. Categories not listed here default
# to ANSWER.
_TYPE_STANCE: dict[QuestionType, Stance] = {
    QuestionType.HALLUCINATION_BAIT: Stance.REFUSE,
    QuestionType.ABSENCE_PROBE: Stance.REFUSE,
    QuestionType.OUT_OF_KB: Stance.REFUSE,
    QuestionType.GAP_PROBE: Stance.HEDGE,
    QuestionType.TERM_REDIRECT: Stance.REDIRECT,
}


def infer_stance(question_type: QuestionType, expected_behavior: str) -> Stance:
    """Derive the expected stance from the mapped type and behaviour prose.

    Explicit behaviour wording wins over the type category, because several
    retrieval-labelled questions expect a refusal. The fallback keys off the
    *mapped* `QuestionType`, not the raw legacy label string, so labels whose
    wording doesn't literally contain a cue substring (e.g. "near-name
    discrepancy (...)" mapped to absence_probe) still get the right default.
    """
    text = " ".join(expected_behavior.split()).lower()

    if any(c in text for c in _REFUSE_CUES):
        return Stance.REFUSE
    if any(c in text for c in _REDIRECT_CUES):
        return Stance.REDIRECT
    if any(c in text for c in _HEDGE_CUES):
        return Stance.HEDGE
    return _TYPE_STANCE.get(question_type, Stance.ANSWER)


def parse_question_bank(md: str) -> dict[str, list[dict]]:
    """Split question_bank.md into version -> table rows."""
    out: dict[str, list[dict]] = {}
    marks = [(m.group(1), m.start()) for m in _VERSION_H2.finditer(md)]
    for idx, (version, start) in enumerate(marks):
        end = marks[idx + 1][1] if idx + 1 < len(marks) else len(md)
        rows = []
        for m in _ROW.finditer(md[start:end]):
            rows.append({
                "id": m.group(1).strip(),
                "text": m.group(2).strip(),
                "legacy_type": m.group(3).strip(),
                "expected_behavior": m.group(4).strip(),
            })
        out[version] = rows
    return out


def _blocks(md: str):
    """Split md into (level, title, heading_start, content_start, content_end).

    `level` is None for the leading span before the first ##/### heading
    (still real document content — the file's H1 title and any preamble
    prose — which belongs in the notes, not discarded).
    """
    marks = list(_HEADING.finditer(md))
    blocks = []
    lead_end = marks[0].start() if marks else len(md)
    if lead_end > 0:
        blocks.append((None, None, 0, 0, lead_end))
    for i, m in enumerate(marks):
        content_end = marks[i + 1].start() if i + 1 < len(marks) else len(md)
        blocks.append((len(m.group(1)), m.group(2).strip(), m.start(), m.end(), content_end))
    return blocks


def parse_answer_key(md: str) -> dict[str, str]:
    """question id -> ground truth prose. RESERVE blocks are skipped.

    A question's ground truth is any ### block whose heading starts with its
    id, found anywhere in the document — not only inside a heading literally
    named "Ground truth per question", since not every answer key wraps its
    blocks in one (v5_answer_key.md has none).
    """
    out: dict[str, str] = {}
    for level, title, _h_start, c_start, c_end in _blocks(md):
        if level != 3:
            continue
        m = _QID.match(title)
        if not m:
            continue  # RESERVE and other non-question ### blocks
        out[m.group(1)] = md[c_start:c_end].strip()
    return out


def parse_answer_key_notes(md: str) -> str:
    """Everything that is not per-question ground truth, verbatim."""
    parts = []
    for level, title, h_start, c_start, c_end in _blocks(md):
        if level == 3 and title is not None and _QID.match(title):
            continue
        if level is None:
            parts.append(md[c_start:c_end])
        else:
            parts.append(md[h_start:c_end])
    return "".join(parts).strip() + "\n"


def build_bank(
    version: str,
    rows: list[dict],
    ground_truths: dict[str, str],
    agent: str,
    corpus: str,
    sourcing: str | None,
) -> Bank:
    questions: list[Question] = []
    missing: list[str] = []

    for row in rows:
        gt = ground_truths.get(row["id"])
        if not gt:
            # Fall back to the bank table's shorthand only if the key has nothing,
            # and record which ones need a human pass.
            missing.append(row["id"])
            continue
        question_type = map_legacy_type(row["legacy_type"])
        questions.append(Question(
            id=row["id"],
            text=row["text"],
            type=question_type,
            type_note=row["legacy_type"],
            expected_stance=infer_stance(question_type, row["expected_behavior"]),
            ground_truth=gt,
            checks=Checks(),  # filled by hand; never guessed
        ))

    if missing:
        raise ValueError(
            f"{version}: no ground truth found for {', '.join(missing)}; add the "
            "### block to the answer key before converting"
        )

    return Bank(version=version, agent=agent, corpus=corpus,
                sourcing=sourcing, questions=questions)
