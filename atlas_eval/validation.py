"""Offline checks over the bank corpus. No network, no model, no AWS.

Issue codes produced here:
    SCHEMA               - a bank file failed to parse or validate against the schema
    EMPTY_BANK            - a bank has no questions
    DUPLICATE_ID          - a question id repeats, within a bank or across banks
    ID_PREFIX_MISMATCH    - a question id does not start with "<version>-"
    ID_MALFORMED          - a question id contains whitespace or a control character
    FROZEN_HASH_MISSING   - a frozen bank has no recorded question_sha256
    FROZEN_HASH_MISMATCH  - a frozen bank's questions changed after freezing
    AFTER_DANGLING        - a question's `after` target does not exist in the bank
    AFTER_CYCLE           - the `after` graph contains a cycle
    AFTER_AMBIGUOUS       - two questions declare the same `after` target
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from atlas_eval.dataset import (
    BankLoadError, RunOrderError, compute_question_sha256, load_bank, resolve_run_order,
)
from atlas_eval.models import Bank

# Whitespace (space, tab, newline, ...) or a C0/DEL control character. The real
# ids look like "v3-Q1"; this catches paste accidents and hand-edit damage in
# a bank YAML. The freeze hash is unforgeable regardless of this character
# set, so this is defense in depth rather than a security fix.
_MALFORMED_ID = re.compile(r"[\s\x00-\x1f\x7f]")


@dataclass(frozen=True)
class Issue:
    bank: str
    question_id: str | None
    code: str
    message: str


def validate_bank(bank: Bank, source: str) -> list[Issue]:
    issues: list[Issue] = []

    if not bank.questions:
        return [Issue(source, None, "EMPTY_BANK", "bank contains no questions")]

    counts = Counter(q.id for q in bank.questions)
    for qid, n in sorted(counts.items()):
        if n > 1:
            issues.append(
                Issue(source, qid, "DUPLICATE_ID", f"id appears {n} times in this bank")
            )

    prefix = f"{bank.version}-"
    for q in bank.questions:
        if not q.id.startswith(prefix):
            issues.append(
                Issue(source, q.id, "ID_PREFIX_MISMATCH",
                      f"id does not start with '{prefix}'")
            )
        match = _MALFORMED_ID.search(q.id)
        if match:
            issues.append(
                Issue(source, q.id, "ID_MALFORMED",
                      f"id contains whitespace or a control character: {match.group()!r}")
            )

    if bank.frozen_on is not None:
        if not bank.question_sha256:
            issues.append(
                Issue(source, None, "FROZEN_HASH_MISSING",
                      f"frozen_on is {bank.frozen_on} but question_sha256 is absent")
            )
        else:
            actual = compute_question_sha256(bank)
            if actual != bank.question_sha256:
                issues.append(
                    Issue(source, None, "FROZEN_HASH_MISMATCH",
                          "question ids or text changed after freezing "
                          f"(recorded {bank.question_sha256[:12]}, actual {actual[:12]}); "
                          "bump the version rather than editing a frozen question")
                )

    try:
        resolve_run_order(bank)
    except RunOrderError as err:
        first = err.question_ids[0] if err.question_ids else None
        issues.append(Issue(source, first, err.code, str(err)))

    return issues


def validate_dir(banks_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    banks: list[tuple[Bank, str]] = []

    for path in sorted(banks_dir.glob("*.yaml")):
        try:
            banks.append((load_bank(path), path.name))
        except BankLoadError as err:
            issues.append(Issue(path.name, None, "SCHEMA", err.detail))

    for bank, source in banks:
        issues.extend(validate_bank(bank, source))

    # Cross-bank duplicate ids. Dedupe to the *set* of ids present in each
    # bank before comparing against `seen`: a bank whose own questions
    # already repeat an id (validate_bank's own DUPLICATE_ID above) would
    # otherwise generate one cross-bank report per repeated occurrence,
    # which is noise on top of the intra-bank report already produced.
    seen: dict[str, str] = {}
    for bank, source in banks:
        ids_in_bank = sorted({q.id for q in bank.questions})
        for qid in ids_in_bank:
            if qid in seen and seen[qid] != source:
                issues.append(
                    Issue(source, qid, "DUPLICATE_ID",
                          f"id also defined in {seen[qid]}")
                )
            seen.setdefault(qid, source)

    return issues
