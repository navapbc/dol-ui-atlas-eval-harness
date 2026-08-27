"""Rescore: reapply the current deterministic scorer to an already-recorded run.

Deterministic scores are computed once, at run time, from whatever the bank's
checks and atlas_eval.scoring said on that day. A later fix to a question's
checks, or to the scorer itself (see scoring.py's dash-folding history), never
reaches runs already on disk: the CSV just keeps repeating the old, wrong
verdict forever. This module recomputes the deterministic columns of a
recorded run's scores.csv against the CURRENT bank and CURRENT scorer,
in place.

Two things must never move as a side effect of that recompute:

* The bank's questions. If a question's id/text changed since the run, the
  recorded answers are answers to a different question, and "rescoring" them
  would silently fabricate comparability across a version boundary that
  should have been a new bank version instead. rescore_run refuses outright
  (RescoreError) rather than guess.

* stance_pass. Whether the agent's stance matched expectation cannot be
  recovered from responses.yaml -- only the answer text is persisted, never
  the observed_stance signal a transport captured at run time. Recomputing
  with observed_stance=None would silently blank (or silently unblock) a
  real stance verdict for every row, which has nothing to do with a checks
  or scorer fix. So stance_pass is carried over from the existing record and
  folded back into deterministic_pass exactly as score_answer would have
  folded it in originally.

Rubric columns (citations/correctness/gap_honesty/scope_discipline/clarity/
total/notes/scored_by/confirmed_by) are human or drafted judgement, not
deterministic output, and this module never touches them.

Migrated legacy runs carry question_sha256 == "legacy-unknown": there is no
recorded hash to verify the bank against, so treating that sentinel as a
match would be exactly the silent-fabrication failure mode this module
exists to prevent. Rather than raise a scary error on the (as of writing) 28
such runs nobody asked to rescore, rescore_run reports them as skipped and
touches nothing.

write_run refuses to write into a non-empty run directory, so this module
never goes through it: it rewrites run_dir/scores.csv directly, reusing
ROLLUP_COLUMNS for column order so it can never drift from write_run's own
output.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from atlas_eval.dataset import compute_question_sha256, load_bank
from atlas_eval.models import Question
from atlas_eval.runs import ROLLUP_COLUMNS, read_run
from atlas_eval.scoring import DeterministicScore, score_answer

LEGACY_UNKNOWN_HASH = "legacy-unknown"


class RescoreError(Exception):
    """Refused: rescoring this run would silently fabricate comparability."""


def _parse_bool(value: str) -> bool | None:
    if value == "True":
        return True
    if value == "False":
        return False
    return None


def _split(joined: str) -> list[str]:
    return joined.split("; ") if joined else []


def _joined(values: list[str]) -> str:
    return "; ".join(values)


def _reconstruct_deterministic(question_id: str, rec: dict) -> DeterministicScore:
    """Rebuild a DeterministicScore from scores.csv's own flattened columns.

    Used as the "before" side of every diff, and as-is for any row this call
    cannot recompute (no bank question or no response for it).
    """
    recall = rec.get("citation_recall") or ""
    return DeterministicScore(
        question_id=question_id,
        stance_pass=_parse_bool(rec.get("stance_pass", "")),
        required_all_pass=rec.get("required_all_pass") == "True",
        required_any_pass=rec.get("required_any_pass") == "True",
        forbidden_pass=rec.get("forbidden_pass") == "True",
        citation_recall=float(recall) if recall else 0.0,
        deterministic_pass=rec.get("deterministic_pass") == "True",
        missing_required=_split(rec.get("missing_required", "")),
        present_forbidden=_split(rec.get("present_forbidden", "")),
        missing_citations=_split(rec.get("missing_citations", "")),
    )


def _rescore_question(question: Question, answer: str, old_rec: dict) -> DeterministicScore:
    """Recompute everything score_answer can derive from the response text,
    but keep the recorded stance_pass (see module docstring)."""
    det = score_answer(question, answer, observed_stance=None)
    old_stance_pass = _parse_bool(old_rec.get("stance_pass", ""))
    deterministic_pass = (
        det.required_all_pass
        and det.required_any_pass
        and det.forbidden_pass
        and det.citation_recall == 1.0
        and old_stance_pass is not False
    )
    return DeterministicScore(
        question_id=question.id,
        stance_pass=old_stance_pass,
        required_all_pass=det.required_all_pass,
        required_any_pass=det.required_any_pass,
        forbidden_pass=det.forbidden_pass,
        citation_recall=det.citation_recall,
        deterministic_pass=deterministic_pass,
        missing_required=det.missing_required,
        present_forbidden=det.present_forbidden,
        missing_citations=det.missing_citations,
    )


def _apply(rec: dict, det: DeterministicScore) -> None:
    """Write det's fields into rec's deterministic columns, matching the
    exact string formatting _row_cells/csv.DictWriter would have produced."""
    rec["stance_pass"] = "" if det.stance_pass is None else str(det.stance_pass)
    rec["required_all_pass"] = str(det.required_all_pass)
    rec["required_any_pass"] = str(det.required_any_pass)
    rec["forbidden_pass"] = str(det.forbidden_pass)
    rec["citation_recall"] = str(round(det.citation_recall, 4))
    rec["deterministic_pass"] = str(det.deterministic_pass)
    rec["missing_required"] = _joined(det.missing_required)
    rec["present_forbidden"] = _joined(det.present_forbidden)
    rec["missing_citations"] = _joined(det.missing_citations)


# Must match the rounding runs.py applies when writing citation_recall.
_CSV_RECALL_PRECISION = 4


@dataclass
class RowDiff:
    question_id: str
    old: DeterministicScore
    new: DeterministicScore

    @property
    def changed(self) -> bool:
        return (
            self.old.required_all_pass != self.new.required_all_pass
            or self.old.required_any_pass != self.new.required_any_pass
            or self.old.forbidden_pass != self.new.forbidden_pass
            # Compare at the precision the CSV stores (runs.py rounds to 4dp).
            # Comparing raw floats reported a change on every rescore -- the old
            # value is read back as 0.3333 while the recomputed one is
            # 0.3333333..., so "0 rows changed" could never be trusted even
            # though the written file was byte-identical.
            or round(self.old.citation_recall, _CSV_RECALL_PRECISION)
            != round(self.new.citation_recall, _CSV_RECALL_PRECISION)
            or self.old.deterministic_pass != self.new.deterministic_pass
            or self.old.missing_required != self.new.missing_required
            or self.old.present_forbidden != self.new.present_forbidden
            or self.old.missing_citations != self.new.missing_citations
        )

    def describe(self) -> str:
        parts = [f"verdict {self.old.deterministic_pass} -> {self.new.deterministic_pass}"]
        for label, old_list, new_list in (
            ("missing_required", self.old.missing_required, self.new.missing_required),
            ("present_forbidden", self.old.present_forbidden, self.new.present_forbidden),
            ("missing_citations", self.old.missing_citations, self.new.missing_citations),
        ):
            if old_list != new_list:
                parts.append(
                    f"{label}: {_joined(old_list) or '(none)'} -> {_joined(new_list) or '(none)'}"
                )
        return f"{self.question_id}: " + "; ".join(parts)


@dataclass
class RescoreResult:
    run_id: str
    status: str  # "rescored" | "unchanged" | "skipped-legacy"
    diffs: list[RowDiff] = field(default_factory=list)
    written: bool = False

    @property
    def changed_diffs(self) -> list[RowDiff]:
        return [d for d in self.diffs if d.changed]


def rescore_run(run_dir: Path, banks_dir: Path, dry_run: bool = False) -> RescoreResult:
    """Recompute run_dir/scores.csv's deterministic columns in place.

    Raises RescoreError (nothing written) if the bank named by the run's
    bank_version has changed questions since the run (its current
    question_sha256 no longer matches the one recorded in run.yaml).

    A run with question_sha256 == "legacy-unknown" is reported as skipped
    and left untouched: see the module docstring for why.
    """
    meta, responses, _rows = read_run(run_dir)

    scores_path = run_dir / "scores.csv"
    with scores_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = tuple(reader.fieldnames or ())
        records = list(reader)
    assert fieldnames == ROLLUP_COLUMNS, (
        f"{scores_path} has unexpected columns; refusing to guess a column mapping"
    )

    if meta.question_sha256 == LEGACY_UNKNOWN_HASH:
        return RescoreResult(run_id=meta.run_id, status="skipped-legacy")

    bank_path = banks_dir / f"{meta.bank_version}.yaml"
    bank = load_bank(bank_path)
    actual = compute_question_sha256(bank)
    if actual != meta.question_sha256:
        raise RescoreError(
            f"{run_dir.name}: refusing to rescore -- {bank_path.name}'s current "
            f"question_sha256 ({actual[:12]}) does not match the hash recorded in "
            f"this run ({meta.question_sha256[:12]}). The bank's questions changed "
            "since this run was scored, so the recorded answers are answers to "
            "different questions; rescoring would silently fabricate comparability. "
            "Bump the bank version instead of rescoring against changed questions."
        )

    by_qid = {q.id: q for q in bank.questions}
    diffs: list[RowDiff] = []
    for rec in records:
        qid = rec["question_id"]
        old_det = _reconstruct_deterministic(qid, rec)
        question = by_qid.get(qid)
        answer = responses.get(qid)
        new_det = (
            _rescore_question(question, answer, rec)
            if question is not None and answer is not None
            else old_det
        )
        diffs.append(RowDiff(qid, old_det, new_det))
        _apply(rec, new_det)

    result = RescoreResult(
        run_id=meta.run_id,
        status="rescored" if any(d.changed for d in diffs) else "unchanged",
        diffs=diffs,
    )

    if result.status == "rescored" and not dry_run:
        with scores_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=ROLLUP_COLUMNS, lineterminator="\n")
            writer.writeheader()
            for rec in records:
                writer.writerow(rec)
        result.written = True

    return result
