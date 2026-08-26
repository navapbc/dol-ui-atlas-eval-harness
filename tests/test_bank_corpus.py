"""Guards over the real migrated corpus, not synthetic fixtures."""

from pathlib import Path

import pytest

from atlas_eval.dataset import load_all_banks, resolve_run_order
from atlas_eval.models import Stance, VerificationStatus
from atlas_eval.validation import validate_dir

BANKS = Path("data/banks")

pytestmark = pytest.mark.skipif(not BANKS.is_dir(), reason="banks not migrated yet")


def test_corpus_validates_clean():
    issues = validate_dir(BANKS)
    assert issues == [], "\n".join(f"{i.bank}:{i.question_id}: {i.code}" for i in issues)


def test_every_question_has_ground_truth():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            assert q.ground_truth.strip(), f"{q.id} has empty ground truth"


def test_every_question_retains_its_legacy_type_note():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            assert q.type_note, f"{q.id} lost its original type label"


def test_check_terms_are_non_empty_strings():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            for name in ("required_all", "required_any", "forbidden", "expect_citations"):
                for term in getattr(q.checks, name):
                    assert term.strip() == term, f"{q.id}: {name} term {term!r} has padding"
                    assert term, f"{q.id}: {name} contains an empty term"


def test_forbidden_terms_are_not_also_required():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            overlap = ({t.lower() for t in q.checks.forbidden}
                       & {t.lower() for t in q.checks.required_all + q.checks.required_any})
            assert not overlap, f"{q.id}: {overlap} is both required and forbidden"


def test_refuse_and_hedge_questions_have_no_required_citations():
    # A question the agent should decline cannot also be required to cite sources.
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            if q.expected_stance in (Stance.REFUSE,):
                assert not q.checks.expect_citations, (
                    f"{q.id} expects a refusal but also requires citations"
                )


def test_run_order_resolves_for_every_bank():
    for bank in load_all_banks(BANKS):
        assert len(resolve_run_order(bank)) == len(bank.questions)


def test_verification_fields_are_consistent():
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            v = q.verification
            if v.status is VerificationStatus.UNVERIFIED:
                assert v.verified_by is None and v.verified_on is None, (
                    f"{q.id} is unverified but records a reviewer"
                )
            if v.status is VerificationStatus.VERIFIED:
                assert v.verified_by, f"{q.id} is verified but names no reviewer"
