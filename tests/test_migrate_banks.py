import pytest

from atlas_eval.migrate.banks import (
    build_bank, infer_stance, parse_answer_key, parse_answer_key_notes,
    parse_question_bank,
)
from atlas_eval.migrate.type_map import LEGACY_TYPE_MAP, map_legacy_type
from atlas_eval.models import QuestionType, Stance

BANK_MD = """# Quick Chat Audit Question Bank

Questions are frozen per version.

## v1 (2026-07-27)

Ground truth in `v1_answer_key.md`.

| ID | Question | Type | Expected behavior |
|----|----------|------|-------------------|
| v1-Q1 | How does the batch process flow? | retrieval | End-to-end flow, or explicit slice |
| v1-Q7 | What does program ZXQQ9999 do? | hallucination bait | Must refuse; does not exist |

## v2 (2026-07-28)

Sourced from real user demand.

| ID | Question | Type | Expected behavior |
|----|----------|------|-------------------|
| v2-Q4 | What are the valid Table 109 values? | gap probe | Must not invent a code list |
"""

KEY_MD = """# v1 Answer Key (backfilled 2026-08-04)

Companion to `question_bank.md` v1.

## Scoring notes specific to v1

- Verified-formula exception applies to Q4.

## Ground truth per question

### v1-Q1 Weekly certification batch flow

The batch layer extracts, audits and reports. Flow: L2DCLNUP then **DXCBDA2R**.

### v1-Q7 ZXQQ9999

No such program. Must refuse.

### RESERVE (cut 2026-08-03, not in the v1 bank): direct deposit

Never run; preserved only.

## Run history (for calibration)

Three graded runs.
"""


def test_every_observed_legacy_type_is_mapped():
    assert len(LEGACY_TYPE_MAP) == 30
    assert map_legacy_type("retrieval (multi-hop, data flow)") is QuestionType.DATA_FLOW
    assert map_legacy_type("brief-derived bait") is QuestionType.HALLUCINATION_BAIT
    assert map_legacy_type("operational scope boundary") is QuestionType.OUT_OF_KB
    assert map_legacy_type("edge / scope") is QuestionType.SCOPE_BOUNDARY


def test_map_legacy_type_is_whitespace_and_case_tolerant():
    assert map_legacy_type("  Gap Probe  ") is QuestionType.GAP_PROBE


def test_unmapped_type_raises_naming_the_string():
    with pytest.raises(KeyError) as exc:
        map_legacy_type("brand new type nobody mapped")
    assert "brand new type nobody mapped" in str(exc.value)


def test_every_map_target_is_a_real_enum_member():
    assert all(isinstance(v, QuestionType) for v in LEGACY_TYPE_MAP.values())


def test_infer_stance_from_legacy_type():
    assert infer_stance("hallucination bait", "Must refuse") is Stance.REFUSE
    assert infer_stance("out-of-KB", "Should decline") is Stance.REFUSE
    assert infer_stance("gap probe", "Should hedge") is Stance.HEDGE
    assert infer_stance("term-redirect", "maps it to ACP") is Stance.REDIRECT
    assert infer_stance("retrieval", "Grounded description") is Stance.ANSWER


def test_infer_stance_prefers_explicit_behaviour_wording():
    # A retrieval question whose expected behaviour demands a refusal.
    assert infer_stance("retrieval", "must say not found") is Stance.REFUSE


def test_parse_question_bank_splits_versions_and_rows():
    parsed = parse_question_bank(BANK_MD)
    assert sorted(parsed) == ["v1", "v2"]
    assert [r["id"] for r in parsed["v1"]] == ["v1-Q1", "v1-Q7"]
    row = parsed["v1"][0]
    assert row["text"] == "How does the batch process flow?"
    assert row["legacy_type"] == "retrieval"
    assert row["expected_behavior"] == "End-to-end flow, or explicit slice"
    assert [r["id"] for r in parsed["v2"]] == ["v2-Q4"]


def test_parse_question_bank_ignores_the_header_separator_row():
    assert all(r["id"].startswith("v") for rows in parse_question_bank(BANK_MD).values()
               for r in rows)


def test_parse_answer_key_extracts_ground_truth_and_skips_reserve():
    gt = parse_answer_key(KEY_MD)
    assert sorted(gt) == ["v1-Q1", "v1-Q7"]
    assert "DXCBDA2R" in gt["v1-Q1"]
    assert "Run history" not in gt["v1-Q1"], "must stop at the next heading"
    assert gt["v1-Q7"].strip() == "No such program. Must refuse."


def test_parse_answer_key_notes_preserves_the_other_sections():
    notes = parse_answer_key_notes(KEY_MD)
    assert "Scoring notes specific to v1" in notes
    assert "Run history" in notes
    assert "RESERVE" in notes, "cut questions are preserved, not discarded"
    assert "Weekly certification batch flow" not in notes


def test_build_bank_produces_valid_questions_with_empty_checks():
    rows = parse_question_bank(BANK_MD)["v1"]
    bank = build_bank("v1", rows, parse_answer_key(KEY_MD),
                      agent="engineering_onboarding_specialist",
                      corpus="quick_space_ca7_daily_s3", sourcing="Ground truth in key.")
    assert bank.version == "v1"
    assert [q.id for q in bank.questions] == ["v1-Q1", "v1-Q7"]
    q1, q7 = bank.questions
    assert q1.type is QuestionType.RETRIEVAL
    assert q1.type_note == "retrieval"
    assert "DXCBDA2R" in q1.ground_truth
    assert q1.checks.required_all == [], "checks are filled by hand, not guessed"
    assert q7.expected_stance is Stance.REFUSE
    assert bank.frozen_on is None and bank.question_sha256 is None


def test_build_bank_errors_when_ground_truth_is_missing():
    rows = parse_question_bank(BANK_MD)["v2"]
    with pytest.raises(ValueError) as exc:
        build_bank("v2", rows, {}, agent="a", corpus="c", sourcing=None)
    assert "v2-Q4" in str(exc.value)
