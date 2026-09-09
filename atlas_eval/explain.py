"""Per-question explanation of a run: why each score is what it is.

`report` gives aggregates and `rubric export` deliberately omits the question,
the key and the answer, so understanding a single score meant opening
transcript.md, the bank YAML and a judged CSV side by side and joining them by
eye. A total of 346/500 is not a finding anyone can act on; "this question
failed because two of its three expected citations were never retrieved, and
the judge marked correctness 1 for omitting the date-offset stage" is.

This module does the join and nothing else. It computes no scores. Everything
it prints is read from the run directory, the bank, or a judged rubric CSV, so
it cannot disagree with the artefacts it is explaining.

The disagreement flag is the part worth reading first. Deterministic scoring
matches substrings; the judge reads. When they diverge sharply, one of them is
wrong about that question, and which one is a finding either way: a
deterministic pass with a low judge score means the checks are over-crediting,
and a deterministic fail with a high judge score means the checks are demanding
the wrong evidence -- or the answer key is.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from atlas_eval.dataset import load_bank, resolve_run_order
from atlas_eval.runs import read_run

DIMENSIONS = ("citations", "correctness", "gap_honesty", "scope_discipline", "clarity")

# A deterministic pass whose judge total falls below this fraction of the
# maximum, or a fail at or above the high mark, is worth a human's attention.
LOW = 0.55
HIGH = 0.70


@dataclass
class QuestionView:
    id: str
    type: str
    expected_stance: str
    verification: str
    text: str
    answer: str
    deterministic_pass: bool | None
    citation_recall: str
    missing_required: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)
    present_forbidden: list[str] = field(default_factory=list)
    required_all: list[str] = field(default_factory=list)
    expect_citations: list[str] = field(default_factory=list)
    judge_scores: dict[str, int] = field(default_factory=dict)
    judge_note: str = ""
    key_dispute: str = ""
    judged_by: str = ""

    @property
    def judge_total(self) -> int | None:
        if not self.judge_scores:
            return None
        return sum(self.judge_scores.values())

    @property
    def judge_max(self) -> int:
        return 2 * len(DIMENSIONS)

    @property
    def disagreement(self) -> str:
        """Empty when the two measures agree well enough to ignore."""
        total = self.judge_total
        if total is None or self.deterministic_pass is None:
            return ""
        fraction = total / self.judge_max
        if self.deterministic_pass and fraction < LOW:
            return (
                "deterministic PASS but judge "
                f"{total}/{self.judge_max} -- the checks may be over-crediting"
            )
        if not self.deterministic_pass and fraction >= HIGH:
            return (
                "deterministic FAIL but judge "
                f"{total}/{self.judge_max} -- the checks, or the key, may be "
                "demanding the wrong evidence"
            )
        return ""


def _split(value: str) -> list[str]:
    return [part for part in (value or "").replace(";", "|").split("|") if part.strip()]


def load_judged(path: Path) -> dict[str, dict]:
    """Read a `rubric judge` output, keyed by question id."""
    with path.open(encoding="utf-8", newline="") as fh:
        return {row["question_id"]: row for row in csv.DictReader(fh)}


def build_views(
    run_dir: Path, banks_dir: Path, judged: Path | None = None
) -> tuple[str, list[QuestionView]]:
    meta, answers, _rows = read_run(run_dir)
    bank_path = banks_dir / f"{meta.bank_version}.yaml"
    questions = resolve_run_order(load_bank(bank_path))

    scores: dict[str, dict] = {}
    scores_csv = run_dir / "scores.csv"
    if scores_csv.is_file():
        with scores_csv.open(encoding="utf-8", newline="") as fh:
            scores = {row["question_id"]: row for row in csv.DictReader(fh)}

    judged_rows = load_judged(judged) if judged and judged.is_file() else {}

    views: list[QuestionView] = []
    for question in questions:
        row = scores.get(question.id, {})
        jrow = judged_rows.get(question.id, {})
        raw_pass = (row.get("deterministic_pass") or "").strip().lower()
        checks = question.checks
        note = jrow.get("notes") or ""
        dispute = ""
        if note.startswith("KEY-DISPUTE:"):
            body = note[len("KEY-DISPUTE:"):]
            dispute, _, note = body.partition("|")
            dispute, note = dispute.strip(), note.strip()
        views.append(
            QuestionView(
                id=question.id,
                type=question.type.value,
                expected_stance=question.expected_stance.value,
                verification=question.verification.status.value,
                text=question.text,
                answer=answers.get(question.id, ""),
                deterministic_pass=(
                    True if raw_pass == "true" else False if raw_pass == "false" else None
                ),
                citation_recall=row.get("citation_recall", ""),
                missing_required=_split(row.get("missing_required", "")),
                missing_citations=_split(row.get("missing_citations", "")),
                present_forbidden=_split(row.get("present_forbidden", "")),
                required_all=list(getattr(checks, "required_all", []) or []),
                expect_citations=list(getattr(checks, "expect_citations", []) or []),
                judge_scores={
                    d: int(jrow[d]) for d in DIMENSIONS if jrow.get(d, "").strip()
                },
                judge_note=note,
                key_dispute=dispute,
                judged_by=jrow.get("scored_by", ""),
            )
        )
    return meta.run_id, views


def _mark(present: bool) -> str:
    return "ok " if present else "MISS"


def format_views(
    run_id: str, views: list[QuestionView], only: str = "all", excerpt: int = 500
) -> str:
    if only == "failures":
        selected = [v for v in views if v.deterministic_pass is False]
    elif only == "disagreements":
        selected = [v for v in views if v.disagreement]
    else:
        selected = views

    out = [f"# {run_id}", ""]
    disagreements = [v for v in views if v.disagreement]
    disputes = [v for v in views if v.key_dispute]
    out.append(
        f"{len(views)} questions | "
        f"deterministic {sum(1 for v in views if v.deterministic_pass)}/{len(views)} | "
        + (
            f"judge {sum(v.judge_total or 0 for v in views)}/"
            f"{sum(v.judge_max for v in views if v.judge_total is not None)}"
            if any(v.judge_total is not None for v in views)
            else "judge not run"
        )
    )
    if disagreements:
        out.append(f"**{len(disagreements)} question(s) where the two measures disagree**")
    if disputes:
        out.append(f"**{len(disputes)} answer key(s) the judge disputes**")
    if only != "all":
        out.append(f"_showing: {only} ({len(selected)} of {len(views)})_")
    out.append("")

    for view in selected:
        total = view.judge_total
        judge_bit = (
            f"judge {total}/{view.judge_max}" if total is not None else "judge not run"
        )
        det = {True: "PASS", False: "FAIL", None: "n/a"}[view.deterministic_pass]
        out += [
            f"## {view.id} — {view.type}",
            "",
            f"- deterministic **{det}** | {judge_bit} | "
            f"expected stance: {view.expected_stance} | key: {view.verification}",
        ]
        if view.judge_scores:
            out.append(
                "- "
                + ", ".join(f"{d} {view.judge_scores[d]}" for d in DIMENSIONS
                            if d in view.judge_scores)
                + (f"  _(judged by {view.judged_by})_" if view.judged_by else "")
            )
        if view.disagreement:
            out += ["", f"> **DISAGREEMENT** — {view.disagreement}"]
        if view.key_dispute:
            out += ["", f"> **KEY DISPUTE** — {view.key_dispute}"]

        out += ["", f"**Question:** {view.text}", ""]

        if view.required_all:
            missing = {m.casefold() for m in view.missing_required}
            out.append("**Must contain:** " + ", ".join(
                f"`{t}` {_mark(t.casefold() not in missing)}" for t in view.required_all))
        if view.expect_citations:
            missing = {m.casefold() for m in view.missing_citations}
            out.append("**Must cite:** " + ", ".join(
                f"`{c}` {_mark(c.casefold() not in missing)}" for c in view.expect_citations)
                + f"  (recall {view.citation_recall})")
        if view.present_forbidden:
            out.append("**Said a forbidden thing:** "
                       + ", ".join(f"`{t}`" for t in view.present_forbidden))
        if view.judge_note:
            out += ["", f"**Judge:** {view.judge_note}"]

        answer = (view.answer or "").strip()
        shown = answer[:excerpt] + ("…" if len(answer) > excerpt else "")
        out += [
            "",
            f"**Answered** ({len(answer)} chars):",
            "",
            "```",
            shown or "(no answer recorded)",
            "```",
            "",
        ]
    return "\n".join(out)
