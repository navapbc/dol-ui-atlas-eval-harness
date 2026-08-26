"""Loading, freeze hashing and run-order resolution for question banks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from atlas_eval.models import Bank, Question

_WS = re.compile(r"\s+")

# Round-trip mode so the same handle can later rewrite a file without
# reordering keys or dropping formatting.
_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True


class BankLoadError(Exception):
    """A bank file could not be parsed or failed schema validation."""

    def __init__(self, path: Path, detail: str) -> None:
        super().__init__(f"{path}: {detail}")
        self.path = path
        self.detail = detail


def normalize_ws(text: str) -> str:
    """Lowercase and collapse all whitespace runs to single spaces."""
    return _WS.sub(" ", text).strip().lower()


def compute_question_sha256(bank: Bank) -> str:
    """Hash the (id, normalized text) pairs, sorted by id.

    Sorting by id makes the hash independent of file position: run order is
    expressed by `after`, not by where a question sits in the list. Ground
    truth and checks are excluded so they stay editable after freezing.

    The pairs are serialized as JSON before hashing, rather than joined with
    plain delimiters, because JSON escapes tabs and newlines inside strings:
    without that, a question id containing those characters could impersonate
    the payload's own delimiters and forge a collision between two genuinely
    different question sets.
    """
    payload = json.dumps(
        [[q.id, normalize_ws(q.text)] for q in sorted(bank.questions, key=lambda q: q.id)],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _describe(err: ValidationError, raw: dict) -> str:
    """Turn pydantic's location paths into messages naming the question id."""
    questions = raw.get("questions") or []
    parts = []
    for e in err.errors():
        loc = e["loc"]
        qid = None
        if len(loc) >= 2 and loc[0] == "questions" and isinstance(loc[1], int):
            if loc[1] < len(questions) and isinstance(questions[loc[1]], dict):
                qid = questions[loc[1]].get("id")
            qid = qid or f"questions[{loc[1]}]"
        field = ".".join(str(p) for p in loc[2:]) or ".".join(str(p) for p in loc)
        parts.append(f"{qid or '<bank>'}: {field}: {e['msg']}")
    return "; ".join(parts)


def load_bank(path: Path) -> Bank:
    with path.open("r", encoding="utf-8") as fh:
        raw = _yaml.load(fh)
    if raw is None:
        raise BankLoadError(path, "file is empty")
    plain = _to_plain(raw)
    try:
        return Bank(**plain)
    except ValidationError as err:
        raise BankLoadError(path, _describe(err, plain)) from err


def _to_plain(node):
    """Strip ruamel's round-trip wrappers so pydantic sees plain containers."""
    if isinstance(node, dict):
        return {str(k): _to_plain(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_to_plain(v) for v in node]
    return node


def _version_key(version: str) -> tuple[int, str]:
    m = re.match(r"v(\d+)$", version)
    return (int(m.group(1)), "") if m else (10**6, version)


def load_all_banks(banks_dir: Path) -> list[Bank]:
    banks = [load_bank(p) for p in sorted(banks_dir.glob("*.yaml"))]
    return sorted(banks, key=lambda b: _version_key(b.version))


class RunOrderError(Exception):
    """The `after` graph cannot be resolved into a single run sequence."""

    def __init__(self, code: str, question_ids: list[str], detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.question_ids = question_ids


def resolve_run_order(bank: Bank) -> list[Question]:
    """Order questions so each `after` question runs immediately after its target.

    Questions without `after` keep file order. A dependent question is spliced
    in directly behind its target, and chains stay contiguous.
    """
    by_id = {q.id: q for q in bank.questions}

    dangling = [q.id for q in bank.questions if q.after and q.after not in by_id]
    if dangling:
        raise RunOrderError(
            "AFTER_DANGLING", dangling,
            f"`after` target not in bank: {', '.join(sorted(dangling))}",
        )

    successors: dict[str, list[str]] = {}
    for q in bank.questions:
        if q.after:
            successors.setdefault(q.after, []).append(q.id)

    ambiguous = sorted(i for ids in successors.values() if len(ids) > 1 for i in ids)
    if ambiguous:
        raise RunOrderError(
            "AFTER_AMBIGUOUS", ambiguous,
            "multiple questions declare the same `after` target, so "
            f"'immediately after' is unsatisfiable: {', '.join(ambiguous)}",
        )

    # Walk each `after` link to its root; a walk that revisits a node is a cycle.
    for q in bank.questions:
        seen, cur = [], q
        while cur.after:
            seen.append(cur.id)
            cur = by_id[cur.after]
            if cur.id in seen:
                raise RunOrderError(
                    "AFTER_CYCLE", sorted(set(seen + [cur.id])),
                    f"`after` cycle through {' -> '.join(seen + [cur.id])}",
                )

    ordered: list[Question] = []
    for q in bank.questions:
        if q.after:
            continue
        ordered.append(q)
        chain = successors.get(q.id, [])
        while chain:
            nxt = by_id[chain[0]]
            ordered.append(nxt)
            chain = successors.get(nxt.id, [])

    if len(ordered) != len(bank.questions):
        placed = {q.id for q in ordered}
        missing = sorted(set(by_id) - placed)
        raise RunOrderError(
            "AFTER_CYCLE", missing,
            f"questions unreachable from any root, indicating a cycle: {', '.join(missing)}",
        )
    return ordered
