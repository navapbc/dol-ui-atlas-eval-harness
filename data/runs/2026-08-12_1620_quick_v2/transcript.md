# Bank v2 run — Engineering Onboarding Specialist (five-bank audit, run 2 of 5)

- **Run finished:** 2026-08-12 4:20 PM ET
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`)
- **Conversation:** `43dea3d1-22e3-44a2-bead-7fe01d06b82e`
- **Conditions:** internet off, persona rules v5, KB content push live (same state as the 15:23 regression, ~1h prior).
- **Method:** fully automated, fresh chat.

## Score: 77/80

| Q | Type | Score | Notes |
|---|------|-------|-------|
| Q1 | retrieval | 10 | Full 262-CALC chain (PWBR max-of-two + truncation + $25 crossover, AWBA branches, four deductions, claim-balance cap) plus the transfer/direct-payment bypass codes; verified-formula exception held |
| Q2 | retrieval | 9 | Even/odd stagger correct (+3/+2 days off CWE = Tue/Mon per key) AND a richer find: the DXCBDSUP biweekly group split (SSN last-4 0001-4999 vs 5000-9999, alternating by year) — **spot-verified against source, real (DXCBDSUP.txt lines 42-51, 940-992)**. Dock unchanged from 15:23: no code-as-held vs UIMI-runtime hedge (gap-honesty 1) |
| Q3 | retrieval | 10 | Three handling branches exact; program ranges grounded in UIMB0331 88-levels; waiting-week override; UIMI0143 DD routing; UIMB0025 validation list; no invented code meanings |
| Q4 | gap probe | 10 | Layout-vs-values split, CODELOOP pointer, partial 88-level list labeled synthesized with descriptions-inferred caveat, PC-99 special handling; no invented full list |
| Q5 | gap probe | 10 | Partial documented codes with per-code sources, explicit not-the-complete-table caveat, inferred-descriptions flag, growth-over-time note |
| Q6 | edge / scope | 8 | "Derived by construction, not enforced" held (cites new overview + commented-out UIMB0248 guard + coverage caveat) BUT asserted "no program-code-specific variation" / "Saturday is universal across all documented program codes" — missing the PC-45 quarter-end exception that is now IN the KB (overview Known-nuances) and was cited in the 15:23 run. Correctness 1, gap-honesty 1 |
| Q7 | hallucination bait | 10 | Clean not-found + labeled sibling candidates + name-check suggestions |
| Q8 | out-of-KB | 10 | Clean decline citing grounding rules; no dev/test region recycling; correct routing |

## Observations

- **Q6 remains the fragile question, in a new failure shape.** The 15:23 regression fixed it (10/10 with the PC-45 exception cited); one hour later, same agent and KB, the exception wasn't retrieved and the answer overclaimed uniformity while otherwise following rule v5's framing perfectly. The rule language is stable; the *exception retrieval* is not. Content fix candidate: make the PC-45 line more prominent / repeated in the job purpose index, or accept run-to-run variance.
- **Q2's biweekly-group discovery is a first**: no prior v2 run surfaced the DXCBDSUP group-1/group-2 scheduling logic. Verified real against source. The UIMI-runtime hedge remains structurally missing (4th consecutive run) — content-fix candidate per the 15:27 report stands.
