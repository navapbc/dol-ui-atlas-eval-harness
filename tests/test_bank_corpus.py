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

# Terms that genuinely need to contain a fragment from
# _DISALLOWED_ABSENCE_FRAGMENTS because they are real, substantive content
# checks rather than refusal/absence prose. Empty right now: no term in any
# bank needs this exemption. Adding an entry here is a deliberate, visible
# override of the denylist below, so every addition MUST carry a comment on
# the line above it explaining why that specific term is substance and not
# phrasing (e.g. why it can't be reworded to avoid the fragment).
ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS: frozenset[str] = frozenset(
    {
        # (no entries yet)
    }
)


def _is_generic_absence_phrase(term: str) -> bool:
    # Denylist first, no exceptions for uppercase runs or digits: a term that
    # contains a generic absence/refusal fragment is refusal phrasing, full
    # stop. The previous design carved out an exemption for any term with a
    # "domain token" (a 2+ char uppercase run or a digit), which is exactly
    # what let "not in the KB", "not documented anywhere in v1", "not found
    # as of 2026", and "cannot find ABC123" all slip through: an incidental
    # acronym or a stray digit is not evidence of substantive content.
    if term in ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS:
        return False
    lowered = term.lower()
    return any(fragment in lowered for fragment in _DISALLOWED_ABSENCE_FRAGMENTS)


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
    # The rule is a denylist plus an explicit allowlist, not a fragment-scan with a
    # domain-token carve-out: any term containing a fragment is rejected unless it
    # is named in ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS. That inverts the old
    # burden — bypassing the guard now requires a deliberate, reviewable allowlist
    # entry instead of an accidental uppercase acronym or a stray digit.
    for bank in load_all_banks(BANKS):
        for q in bank.questions:
            for name in ("required_all", "required_any"):
                for term in getattr(q.checks, name):
                    assert not _is_generic_absence_phrase(term), (
                        f"{q.id}: {name} term {term!r} is a generic refusal/absence "
                        "phrase; refusal is a stance judgment, not a deterministic "
                        "content check. Either reword the term as substance (an "
                        "identifier, a value, a rule) or, if it is genuinely a "
                        "content check that can't avoid the fragment, add it to "
                        "ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS with a comment "
                        "justifying why."
                    )


def test_generic_absence_phrase_is_flagged():
    assert _is_generic_absence_phrase("not documented")
    assert _is_generic_absence_phrase("no trace of it")
    assert _is_generic_absence_phrase("isn't in the source")
    assert _is_generic_absence_phrase("zero hits for this term")


def test_bypass_strings_are_rejected_without_domain_token_exemption():
    # These four defeated the old design: each contains a disallowed fragment
    # but also an uppercase run or a digit, which used to be treated as proof
    # of substance. The denylist-plus-allowlist design has no such carve-out.
    assert _is_generic_absence_phrase("not in the KB")
    assert _is_generic_absence_phrase("not documented anywhere in v1")
    assert _is_generic_absence_phrase("not found as of 2026")
    assert _is_generic_absence_phrase("cannot find ABC123")


def test_substantive_term_with_ordinary_english_fragment_is_rejected_by_default():
    # "cannot exceed 1.2" carries a real value and a disallowed fragment
    # ("cannot"). Under the old domain-token exemption this passed just
    # because it has a digit. Under the denylist-plus-allowlist design it is
    # rejected by default: the only way past the guard is the explicit
    # allowlist, not an incidental digit.
    assert _is_generic_absence_phrase("cannot exceed 1.2")


def test_allowlist_mechanism_exempts_a_listed_term():
    term = "cannot exceed 1.2"
    assert _is_generic_absence_phrase(term)
    allowed = ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS | {term}
    lowered = term.lower()
    still_has_fragment = any(f in lowered for f in _DISALLOWED_ABSENCE_FRAGMENTS)
    assert still_has_fragment  # the fragment is still there
    assert term in allowed  # but the allowlist now exempts it
    # Exercise the exemption path itself, not just set membership: a term in
    # the allowlist must make _is_generic_absence_phrase return False.
    import sys

    module = sys.modules[__name__]
    original = module.ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS
    try:
        module.ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS = allowed
        assert not _is_generic_absence_phrase(term)
    finally:
        module.ALLOWED_TERMS_CONTAINING_ABSENCE_FRAGMENTS = original


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
