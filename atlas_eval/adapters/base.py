"""The one interface every backend implements.

An adapter's only job is to get raw answer text out of a backend, in the order
asked. It never scores, never writes a run record, and never authenticates.
Keeping that boundary is what makes a Quick run and a future Bedrock run
comparable: the same orchestrator, the same scorer, the same record.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from atlas_eval.models import Question, Stance


class Response(BaseModel):
    """One backend answer, exactly as returned. Never post-processed here."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    answer: str
    asked_at: datetime
    citations: list[str] = Field(default_factory=list)
    # Supplied only when the transport can observe it (for example a UI refusal
    # marker). Otherwise a human sets it during review. Never inferred by model.
    observed_stance: Stance | None = None


class AskResult(BaseModel):
    """The outcome of asking a whole bank in one conversation."""

    model_config = ConfigDict(extra="forbid")

    responses: list[Response] = Field(default_factory=list)
    conversation_id: str | None = None
    complete: bool = False
    failure: str | None = None


class TransportError(Exception):
    """A transport could not continue. Codes are stable; messages are not."""

    CODES = (
        "AUTH_REQUIRED",
        "SELECTOR_MISSING",
        "TIMEOUT",
        "CONVERSATION_LOST",
        "PARSE_FAILED",
    )

    def __init__(self, code: str, detail: str) -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown TransportError code: {code!r}")
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@runtime_checkable
class Backend(Protocol):
    """Implemented by the Quick adapter now, Bedrock and a local LLM later."""

    name: str
    transport: str

    def snapshot(self) -> dict:
        """Config that makes a later score interpretable. Read-only."""
        ...

    def ask(self, questions: list[Question]) -> AskResult:
        """Ask in the given order, in ONE conversation, and return raw answers.

        The order is already resolved by resolve_run_order and must not be
        changed: several questions only work immediately after their predecessor.
        """
        ...
