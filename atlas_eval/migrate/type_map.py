"""Mapping from the 30 legacy free-text type labels to the controlled enum.

The legacy `type` column was free text and drifted across six banks. Each
original string is preserved verbatim in Question.type_note, so this mapping is
auditable and reversible.
"""

from __future__ import annotations

from atlas_eval.models import QuestionType as T

LEGACY_TYPE_MAP: dict[str, T] = {
    # plain retrieval and its qualified variants
    "retrieval": T.RETRIEVAL,
    "retrieval (active workstream)": T.RETRIEVAL,
    "retrieval (data architecture)": T.RETRIEVAL,
    "retrieval (multi-hop chain)": T.RETRIEVAL,
    "retrieval (retest of v3-q4 miss)": T.RETRIEVAL,
    # tracing records through a chain
    "retrieval (multi-hop, data flow)": T.DATA_FLOW,
    "data flow (conflict surfacing)": T.DATA_FLOW,
    "conflict surfacing": T.DATA_FLOW,
    # business rules and computations
    "rule logic": T.RULE_LOGIC,
    "rule logic (design intent)": T.RULE_LOGIC,
    # asks for something known to be absent; must hedge
    "gap probe": T.GAP_PROBE,
    # plausible-sounding nonexistent entity; must refuse
    "hallucination bait": T.HALLUCINATION_BAIT,
    "brief-derived bait": T.HALLUCINATION_BAIT,
    "spec-derived bait / scope boundary": T.HALLUCINATION_BAIT,
    "artifact-class bait (rule a)": T.HALLUCINATION_BAIT,
    # near-name family baits
    "absence probe (near-name family bait)": T.ABSENCE_PROBE,
    "near-name discrepancy (rule a both directions + rule c)": T.ABSENCE_PROBE,
    # real process under the wrong name
    "term-redirect": T.TERM_REDIRECT,
    "term disambiguation / scope boundary": T.TERM_REDIRECT,
    # expand an acronym the KB defines
    "acronym check": T.ACRONYM_CHECK,
    # tests the edge of what the linked spaces cover
    "edge / scope": T.SCOPE_BOUNDARY,
    "boundary probe (split scope)": T.SCOPE_BOUNDARY,
    "retrieval + scope boundary": T.SCOPE_BOUNDARY,
    "retrieval + system boundary": T.SCOPE_BOUNDARY,
    "scope discipline (cwe retest, re-angled)": T.SCOPE_BOUNDARY,
    # operational or access information that is not in the KB at all
    "out-of-kb": T.OUT_OF_KB,
    "operational scope boundary": T.OUT_OF_KB,
    # retrieval spanning linked spaces
    "cross-space": T.CROSS_SPACE,
    # asks the agent to generate an artifact rather than retrieve
    "generation probe (rule d)": T.GENERATION_PROBE,
    # asks what happens at a handoff to another team or system
    "handoff probe (rule e)": T.HANDOFF_PROBE,
}


def map_legacy_type(raw: str) -> T:
    key = " ".join(raw.split()).lower()
    if key not in LEGACY_TYPE_MAP:
        raise KeyError(
            f"unmapped legacy type {raw!r}; add it to LEGACY_TYPE_MAP rather than "
            "guessing a category"
        )
    return LEGACY_TYPE_MAP[key]
