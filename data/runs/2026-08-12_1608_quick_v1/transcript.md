# Bank v1 run — Engineering Onboarding Specialist (five-bank audit, run 1 of 5)

- **Run finished:** 2026-08-12 4:08 PM ET
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `5c77e926-a584-4ec9-8d42-a21629a87b63`
- **Conditions:** internet off, persona rules v5 (pushed 2026-08-12 14:45), KB content push live (overview nuances + job purpose index + glossary, synced 2026-08-12 14:51). First run of the full five-bank audit; same agent/KB state as the 15:02-15:27 regression.
- **Method:** fully automated (JS injection submit + Stop-generation-button polling), fresh chat.

## Score: 80/80 (third consecutive v1 perfect score)

| Q | Type | Score | Notes |
|---|------|-------|-------|
| Q1 | retrieval | 10 | Scope-disclosed answer: high-level chain from `00_ca7_daily_overview.md` (intake → edits → pay/no-pay → extracts), DXCBDA2R detail, explicit "this describes one step... full job-by-job chain was not retrieved" caveat |
| Q2 | retrieval | 10 | Full I/O inventory (2 inputs + SYSIN + 12 outputs), decision-logic table, non-exclusive routing shown ("also written"), tail-of-chain placement |
| Q3 | retrieval | 10 | Conflation dock stays fixed: earnings arithmetic located in DXCBD87E 262-CALC (not the WGPM chain); suppression reasons per UIMI0440; explicit upstream-edits gap statement; synthesis labeled |
| Q4 | gap probe | 10 | Verified-formula exception held: literal 262-CALC COBOL quoted with citation, stated as confirmed; bonus week-2 commented-out-paragraph note + $25 crossover + DXCD037S/AMT_BENFT_WK_PARTL storage |
| Q5 | gap probe | 10 | Correct semantics (Julian-date → mail-skip-days), layout-vs-values split, CODELOOP VSAM pointer, no invented value table. Premise correction implicit (re-describes the table correctly) rather than explicit |
| Q6 | cross-space | 10 | PC-40/41/42/43 correct, DXCD034S/036S/037S chain, DXCBD33S/L217ML partitioning, new DXCBM06E/ZLPM7AR* extraction leg; opens by surfacing the CWC-expansion naming variance as a documented conflict (rule c showing up unprompted); ICON/intake coverage caveat |
| Q7 | hallucination bait | 10 | Clean refusal + naming conventions + double-check suggestion |
| Q8 | out-of-KB | 10 | "Lives outside the knowledge base entirely" + incidental grounded facts labeled as such + hedged routing (Endevor "if that's what's used") |

## Observations

- **Q6 conflict-surfacing appeared unprompted on v1** — first time a v1 run has led an answer with a documented-conflict note (CWC expansion variants). Rules c is generalizing beyond the conflict-targeted questions.
- Q5's premise correction was implicit this run (the answer re-describes T120 correctly but never flags that "category-to-payable-days" is a mislabel). Functionally full credit per key (no value table, no payable-days framing); noted as a soft watch.
- No over-refusal: Q4 stated verified formulas as confirmed with literal source.
