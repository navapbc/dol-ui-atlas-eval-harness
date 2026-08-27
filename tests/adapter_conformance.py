"""A runtime conformance check for Backend implementations.

`runtime_checkable` on the `Backend` Protocol only confirms that the named
attributes and methods exist. It does not check `ask()`'s return type, the
shape of `.responses`, or ordering. This project runs no static type checker,
so those defects only surface later during scoring, far from the boundary
meant to catch them.

`assert_backend_conformance` is the boundary check: it exercises a backend
against a real question list and asserts every part of the contract that
`isinstance(backend, Backend)` cannot see. It is a test helper only and must
not be imported from `atlas_eval/`.
"""

from __future__ import annotations

from atlas_eval.adapters.base import AskResult, Response
from atlas_eval.models import Question


def assert_backend_conformance(backend, questions: list[Question]) -> None:
    """Assert that `backend` fulfills the Backend contract against `questions`.

    Raises AssertionError, with a message naming what failed, on the first
    violation found.
    """
    assert isinstance(backend.name, str) and backend.name, (
        f"backend.name must be a non-empty string, got {backend.name!r}"
    )
    assert isinstance(backend.transport, str) and backend.transport, (
        f"backend.transport must be a non-empty string, got {backend.transport!r}"
    )

    snapshot = backend.snapshot()
    assert isinstance(snapshot, dict), (
        f"backend.snapshot() must return a dict, got {type(snapshot).__name__}"
    )

    result = backend.ask(questions)
    assert isinstance(result, AskResult), (
        "backend.ask(questions) must return an AskResult instance, got "
        f"{type(result).__name__}. Returning a bare list/tuple/dict of "
        "responses satisfies the runtime_checkable Protocol but is not "
        "a conformant backend."
    )

    for response in result.responses:
        assert isinstance(response, Response), (
            "every element of AskResult.responses must be a Response "
            f"instance, got {type(response).__name__}"
        )

    asked_ids = [q.id for q in questions]
    asked_id_set = set(asked_ids)

    for response in result.responses:
        assert response.question_id in asked_id_set, (
            f"response.question_id {response.question_id!r} was not among "
            f"the ids asked: {asked_ids!r}. An adapter must not invent an id."
        )

    returned_ids = [r.question_id for r in result.responses]
    assert len(returned_ids) == len(set(returned_ids)), (
        f"AskResult.responses contains duplicate question_id values: {returned_ids!r}"
    )

    expected_order = [qid for qid in asked_ids if qid in returned_ids]
    assert returned_ids == expected_order, (
        "AskResult.responses must preserve the relative order of the "
        f"questions given. Expected order {expected_order!r}, got "
        f"{returned_ids!r}. Several questions in the real corpus only work "
        "immediately after their predecessor; reordering silently destroys "
        "the probe."
    )

    assert isinstance(result.complete, bool), (
        f"AskResult.complete must be a bool, got {type(result.complete).__name__}"
    )
    if result.complete is False:
        assert isinstance(result.failure, str) and result.failure, (
            "AskResult.failure must be a non-empty string when complete is "
            f"False, got {result.failure!r}. A failed run must say why."
        )
