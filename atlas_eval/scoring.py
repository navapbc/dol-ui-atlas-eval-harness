"""Deterministic scoring and the rubric datatype.

The deterministic layer is literal, case-insensitive and whitespace-normalized:
no stemming, no fuzzy matching, no semantic similarity. A scorer whose behaviour
can drift silently rewrites every historical number, so the rules here are
intentionally dumb and stable, and this module never calls a model.

The rubric layer is filled by the audit workflow, where an LLM drafts scores
against the answer key and a human reviews them. Rubric.scored_by and
Rubric.confirmed_by record that provenance so reports can be restricted to
human-confirmed rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from atlas_eval.dataset import normalize_ws
from atlas_eval.models import Question, Stance

RUBRIC_DIMENSIONS: tuple[str, ...] = (
    "citations",
    "correctness",
    "gap_honesty",
    "scope_discipline",
    "clarity",
)


class Rubric(BaseModel):
    """The five scored dimensions, 0-2 each, plus scoring provenance."""

    model_config = ConfigDict(extra="forbid")

    citations: int | None = Field(default=None, ge=0, le=2)
    correctness: int | None = Field(default=None, ge=0, le=2)
    gap_honesty: int | None = Field(default=None, ge=0, le=2)
    scope_discipline: int | None = Field(default=None, ge=0, le=2)
    clarity: int | None = Field(default=None, ge=0, le=2)
    notes: str | None = None

    # Who or what produced these values: a model id such as "claude-opus-5", or a
    # person's name for a hand-scored row.
    scored_by: str | None = None
    # The person who reviewed them. None means nobody has yet.
    confirmed_by: str | None = None

    @property
    def total(self) -> int | None:
        """Sum out of 10, or None until every dimension is scored."""
        values = [getattr(self, d) for d in RUBRIC_DIMENSIONS]
        if any(v is None for v in values):
            return None
        return sum(values)

    @property
    def is_confirmed(self) -> bool:
        """True once a human has signed off on these values."""
        return bool(self.confirmed_by)


@dataclass
class DeterministicScore:
    question_id: str
    stance_pass: bool | None
    required_all_pass: bool
    required_any_pass: bool
    forbidden_pass: bool
    citation_recall: float
    deterministic_pass: bool
    missing_required: list[str] = field(default_factory=list)
    present_forbidden: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)


def _contains(haystack: str, needle: str) -> bool:
    return normalize_ws(needle) in haystack


def score_answer(
    question: Question,
    answer: str,
    observed_stance: Stance | None = None,
) -> DeterministicScore:
    """Score one answer against one question's checks.

    observed_stance is supplied by a human reviewer or by a transport signal.
    Stance cannot be inferred from text without a model, and models are barred
    from scoring, so an unobserved stance yields stance_pass=None and does not
    fail deterministic_pass.
    """
    hay = normalize_ws(answer)
    checks = question.checks

    missing_required = [t for t in checks.required_all if not _contains(hay, t)]
    required_all_pass = not missing_required

    required_any_pass = (
        True if not checks.required_any
        else any(_contains(hay, t) for t in checks.required_any)
    )

    present_forbidden = [t for t in checks.forbidden if _contains(hay, t)]
    forbidden_pass = not present_forbidden

    missing_citations = [c for c in checks.expect_citations if not _contains(hay, c)]
    if checks.expect_citations:
        found = len(checks.expect_citations) - len(missing_citations)
        citation_recall = found / len(checks.expect_citations)
    else:
        citation_recall = 1.0

    stance_pass = None if observed_stance is None else (
        observed_stance == question.expected_stance
    )

    deterministic_pass = (
        required_all_pass
        and required_any_pass
        and forbidden_pass
        and citation_recall == 1.0
        and stance_pass is not False
    )

    return DeterministicScore(
        question_id=question.id,
        stance_pass=stance_pass,
        required_all_pass=required_all_pass,
        required_any_pass=required_any_pass,
        forbidden_pass=forbidden_pass,
        citation_recall=citation_recall,
        deterministic_pass=deterministic_pass,
        missing_required=missing_required,
        present_forbidden=present_forbidden,
        missing_citations=missing_citations,
    )
