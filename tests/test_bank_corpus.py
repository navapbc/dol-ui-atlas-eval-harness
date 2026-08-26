"""Guards over the real migrated corpus, not synthetic fixtures."""

import re
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


_DISALLOWED_ABSENCE_FRAGMENTS = (
    "not found",
    "does not exist",
    "doesn't exist",
    "no such",
    "not available",
    "not documented",
    "not in the kb",
    "isn't in",
    "cannot",
    "could not",
    "unable",
    "no evidence",
    "not present",
    "zero hits",
    "no trace",
    "outside what i have",
)

# A run of two-or-more uppercase letters (an identifier like "DXCBD87E" or "WBR")
# or any digit. Either one marks a term as domain-specific rather than generic
# absence prose, regardless of which _DISALLOWED_ABSENCE_FRAGMENTS substring it
# also happens to contain.
_DOMAIN_TOKEN = re.compile(r"[A-Z]{2,}|\d")


def _is_generic_absence_phrase(term: str) -> bool:
    lowered = term.lower()
    has_fragment = any(fragment in lowered for fragment in _DISALLOWED_ABSENCE_FRAGMENTS)
    if not has_fragment:
        return False
    # A domain-specific token (an identifier or a number) makes the term
    # substantive even though it also contains an ordinary-English fragment,
    # e.g. "cannot exceed 1.2" or "DXCBD87E not present".
    return not _DOMAIN_TOKEN.search(term)


def test_required_terms_are_not_generic_refusal_phrasing():
    # required_all/required_any must key on substance (identifiers, values, rules),
    # not on how a refusal happens to be worded. Refusal is a stance judgment
    # (expected_stance compared against an observed_stance supplied by a human or a
    # transport signal), not something the deterministic layer should string-match.
    # A term like "not found" or "could not" fails a correctly-worded refusal that an
    # agent phrases differently, generating exactly the score instability the
    # deterministic layer exists to remove. This guards every bank, including the
    # not-yet-populated v4-v6, so this class of defect can't return.
    #
    # The rule is sharper than a bare fragment scan: a term is only flagged when it
    # contains a generic absence fragment AND has no domain-specific token (no
    # uppercase identifier of two-or-more characters, no digit). That keeps a future
    # substantive term such as "cannot exceed 1.2" or "DXCBD87E not present" legal
    # while still catching "not documented" or "no trace".
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            for name in ("required_all", "required_any"):
                for term in getattr(q.checks, name):
                    assert not _is_generic_absence_phrase(term), (
                        f"{q.id}: {name} term {term!r} is a generic refusal/"
                        "absence phrase with no domain-specific token; refusal is "
                        "a stance judgment, not a deterministic content check"
                    )


def test_generic_absence_phrase_is_flagged():
    assert _is_generic_absence_phrase("not documented")
    assert _is_generic_absence_phrase("no trace of it")
    assert _is_generic_absence_phrase("isn't in the source")
    assert _is_generic_absence_phrase("zero hits for this term")


def test_substantive_term_with_ordinary_english_fragment_is_allowed():
    # These contain a fragment from the disallowed list ("cannot", "unable",
    # "no evidence", "not present") but are legitimate domain content because
    # they carry a number or an uppercase identifier.
    assert not _is_generic_absence_phrase("cannot exceed 1.2")
    assert not _is_generic_absence_phrase("DXCBD87E not present")
    assert not _is_generic_absence_phrase("unable to exceed WBR")
    assert not _is_generic_absence_phrase("no evidence of PWBR above 5")


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
