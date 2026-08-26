import pytest

from atlas_eval.migrate.banks import (
    _resolve_cue_stance, build_bank, infer_stance, parse_answer_key,
    parse_answer_key_notes, parse_question_bank, parse_reserve_block,
    resolve_reserve_pointer,
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


def test_infer_stance_from_mapped_type():
    assert infer_stance(QuestionType.HALLUCINATION_BAIT, "Must refuse") is Stance.REFUSE
    assert infer_stance(QuestionType.OUT_OF_KB, "Should decline") is Stance.REFUSE
    assert infer_stance(QuestionType.GAP_PROBE, "Should hedge") is Stance.HEDGE
    assert infer_stance(QuestionType.TERM_REDIRECT, "maps it to ACP") is Stance.REDIRECT
    assert infer_stance(QuestionType.RETRIEVAL, "Grounded description") is Stance.ANSWER


def test_infer_stance_prefers_explicit_behaviour_wording():
    # A retrieval question whose expected behaviour demands a refusal.
    assert infer_stance(QuestionType.RETRIEVAL, "must say not found") is Stance.REFUSE


def test_infer_stance_uses_mapped_type_not_raw_label_substring():
    # Regression: these legacy labels don't contain the fallback's old
    # substrings ("bait", "out-of-kb", "gap probe", ...) but the type map
    # correctly routes them to absence_probe / out_of_kb, so the fallback
    # must key off the mapped type rather than the raw label string.
    near_name = map_legacy_type("near-name discrepancy (rule a both directions + rule c)")
    assert near_name is QuestionType.ABSENCE_PROBE
    assert infer_stance(near_name, "Flags the discrepancy for confirmation") is Stance.REFUSE

    operational = map_legacy_type("operational scope boundary")
    assert operational is QuestionType.OUT_OF_KB
    assert infer_stance(operational, "Not in KB; clean KB-bounded answer") is Stance.REFUSE


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


# --- Finding 1: cue specificity, not list order, decides the stance -------


def test_resolve_cue_stance_longest_match_wins_regardless_of_list_order():
    # Synthetic cues unrelated to the real _REFUSE_CUES/_HEDGE_CUES lists, so
    # the general rule is pinned independently of the real cue data.
    cues = [("zzz alpha", Stance.REFUSE), ("zzz alpha beta gamma", Stance.HEDGE)]
    text = "some prose containing zzz alpha beta gamma in the middle"
    assert _resolve_cue_stance(text, cues) is Stance.HEDGE

    # Flip the list order: the longer cue must still win.
    flipped = [("zzz alpha beta gamma", Stance.HEDGE), ("zzz alpha", Stance.REFUSE)]
    assert _resolve_cue_stance(text, flipped) is Stance.HEDGE

    # Only the short cue is present -> its stance, not the longer one's.
    assert _resolve_cue_stance("zzz alpha only, no gamma here", cues) is Stance.REFUSE

    # Neither cue present -> no opinion.
    assert _resolve_cue_stance("nothing relevant here", cues) is None


def test_infer_stance_specific_hedge_cue_beats_broad_refuse_cue():
    # v2-Q4's own expected-behavior text: the broad "must not invent" refuse
    # cue is a substring of the narrower "must not invent a code list" hedge
    # cue. The longer, more specific cue must win.
    text = "Layout exists in the copybook; must not invent a code list"
    assert infer_stance(QuestionType.GAP_PROBE, text) is Stance.HEDGE


def test_infer_stance_bare_refuse_cue_still_wins_when_alone():
    # Same broad cue, but with no more-specific hedge cue present: refuse.
    assert infer_stance(QuestionType.GAP_PROBE, "must not invent") is Stance.REFUSE


# --- Finding 2: RESERVE pointers resolve to real ground-truth prose -------


_RESERVE_KEY_MD = """# v3 Answer Key

## Ground truth per question

### v3-Q1 Something else entirely

Not the RESERVE prose; must not leak into the resolved block.

### RESERVE (cut 2026-08-03, not in the v3 bank): self-service direct deposit

Verified in space: UIMT_DIR_DEP_INFO carries IDN_CONVERSATION; 'WEB ' marks
online self-service changes (UIMB0803 daily extract).

## Errata

Not part of the RESERVE block either.
"""


def test_parse_reserve_block_extracts_only_the_reserve_prose():
    block = parse_reserve_block(_RESERVE_KEY_MD)
    assert block is not None
    assert "IDN_CONVERSATION" in block
    assert "Something else entirely" not in block
    assert "Not part of the RESERVE block" not in block


def test_parse_reserve_block_returns_none_when_absent():
    assert parse_reserve_block("# no reserve here\n\n### v1-Q1 x\n\nprose\n") is None


def test_resolve_reserve_pointer_merges_prose_and_returns_pointer_as_provenance():
    pointer = "Ground truth in v3_answer_key.md §RESERVE: short summary of the real prose"
    resolved, provenance = resolve_reserve_pointer(
        pointer, {"v3_answer_key.md": _RESERVE_KEY_MD}
    )
    assert "IDN_CONVERSATION" in resolved
    assert "Something else entirely" not in resolved
    assert provenance == pointer


def test_resolve_reserve_pointer_is_a_noop_for_ordinary_ground_truth():
    gt = "The batch layer extracts, audits and reports."
    resolved, provenance = resolve_reserve_pointer(gt, {})
    assert resolved == gt
    assert provenance is None


def test_resolve_reserve_pointer_raises_when_source_file_missing():
    with pytest.raises(ValueError, match="v9_answer_key.md"):
        resolve_reserve_pointer("Ground truth in v9_answer_key.md §RESERVE: x", {})


def test_resolve_reserve_pointer_raises_when_source_has_no_reserve_block():
    with pytest.raises(ValueError, match="RESERVE"):
        resolve_reserve_pointer(
            "Ground truth in v9_answer_key.md §RESERVE: x",
            {"v9_answer_key.md": "# no reserve block here\n"},
        )


def test_build_bank_resolves_reserve_pointer_and_keeps_provenance():
    rows = [{
        "id": "v6-Q9",
        "text": "How does LOOPS record self-service direct deposit changes?",
        "legacy_type": "retrieval + scope boundary",
        "expected_behavior": "Ground truth in v3_answer_key.md §RESERVE.",
    }]
    pointer = "Ground truth in v3_answer_key.md §RESERVE: short summary of the real prose"
    bank = build_bank(
        "v6", rows, {"v6-Q9": pointer}, agent="a", corpus="c", sourcing=None,
        reserve_sources={"v3_answer_key.md": _RESERVE_KEY_MD},
    )
    q = bank.questions[0]
    assert "IDN_CONVERSATION" in q.ground_truth
    assert "Ground truth in v3_answer_key.md §RESERVE" not in q.ground_truth
    assert q.provenance == pointer


def test_build_bank_leaves_provenance_none_for_non_pointer_ground_truth():
    rows = parse_question_bank(BANK_MD)["v1"]
    bank = build_bank("v1", rows, parse_answer_key(KEY_MD), agent="a", corpus="c",
                      sourcing=None, reserve_sources={"v3_answer_key.md": _RESERVE_KEY_MD})
    assert all(q.provenance is None for q in bank.questions)
