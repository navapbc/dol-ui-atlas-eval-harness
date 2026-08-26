"""Loading, freeze hashing and run-order resolution for question banks."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML

from atlas_eval.models import Bank

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
