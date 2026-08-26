"""Typed models for question banks and their verification state.

Field names here are load-bearing: they are the YAML keys in data/banks/*.yaml
and the column sources for the SME review spreadsheet.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QuestionType(str, Enum):
    """Controlled vocabulary so scores aggregate by type.

    The legacy banks used free text and drifted to 30 distinct strings; the
    original label is preserved verbatim in Question.type_note.
    """

    RETRIEVAL = "retrieval"
    RULE_LOGIC = "rule_logic"
    DATA_FLOW = "data_flow"
    GAP_PROBE = "gap_probe"
    HALLUCINATION_BAIT = "hallucination_bait"
    ABSENCE_PROBE = "absence_probe"
    TERM_REDIRECT = "term_redirect"
    ACRONYM_CHECK = "acronym_check"
    SCOPE_BOUNDARY = "scope_boundary"
    OUT_OF_KB = "out_of_kb"
    CROSS_SPACE = "cross_space"
    GENERATION_PROBE = "generation_probe"
    HANDOFF_PROBE = "handoff_probe"


class Stance(str, Enum):
    """Coarse behavioural expectation, independent of content correctness."""

    ANSWER = "answer"
    HEDGE = "hedge"
    REFUSE = "refuse"
    REDIRECT = "redirect"


class VerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    NEEDS_SME = "needs-sme"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=False)


class Checks(_Strict):
    """Deterministic, literal match targets. Empty lists mean "no check"."""

    required_all: list[str] = Field(default_factory=list)
    required_any: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    expect_citations: list[str] = Field(default_factory=list)


class Verification(_Strict):
    status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_by: str | None = None
    verified_on: date | None = None
    notes: str | None = None


class Question(_Strict):
    id: str
    text: str
    type: QuestionType
    type_note: str | None = None
    provenance: str | None = None
    expected_stance: Stance
    ground_truth: str
    partial_credit: str | None = None
    after: str | None = None
    checks: Checks = Field(default_factory=Checks)
    verification: Verification = Field(default_factory=Verification)


class Bank(_Strict):
    version: str
    frozen_on: date | None = None
    question_sha256: str | None = None
    agent: str
    corpus: str
    sourcing: str | None = None
    questions: list[Question] = Field(default_factory=list)
