# Quick Chat Agent Audit: Engineering Onboarding Specialist (bank v1, post-KB-fix run)

- **Run finished:** 2026-08-05 4:21 PM ET
- **Agent:** Engineering Onboarding Specialist (`093ac4e3-0712-481e-af95-9ddc5e4fc734`), persona unchanged since 2026-08-03
- **Change under test:** the Daily CA-7 S3 knowledge base was empty from creation (2026-07-24) until today — its include prefix was stored as an `s3://` URI, which matches zero object keys, so every sync completed having ingested nothing (see the 1157 report's addenda). The prefix was corrected to `quick-loops/kb_CA7_daily/` this afternoon; the first real sync ingested **4,977 files, 0 unavailable**. The acceptance probe ("What does job L2UDB020 do?", 4:06 PM) passed with a full grounded answer citing `L2UDB020.md`/`L2UDB020.txt`. This run measures bank v1 with the agent's largest corpus retrievable for the first time.
- **Snapshots:** `snapshots/2026-08-05_1621_*.json` (agent + spaces; small-space doc counts unchanged)
- **Conversation:** `a22187c6-4f96-46f2-8961-10f3c311cb08`
- **Graded against:** `v1_answer_key.md`

## Scorecard

| # | Question | Type | Score | Notes |
|---|----------|------|-------|-------|
| 1 | Weekly cert batch flow | retrieval | 10/10 | Full flow with the scope statement ("batch doesn't decide — it reports"), L2DCLNUP, VSAM snapshot, DXCBDA2R classification detail, AUDITREP distribution, cadence tiers, flat-family note. Now cites daily-space docs (`00_ca7_daily_overview.md`, `DXCBDA2R.md`) alongside the Weekly Cert space. |
| 2 | DXCBDA2R role and I/O | retrieval | 10/10 | Complete I/O inventory with datasets and record lengths; explicitly states the cascading, non-exclusive routing (a top-answer marker per the key); control totals. |
| 3 | Pay vs no-pay rules | retrieval | 10/10 | **The standing one-point conflation dock is fixed.** Three consecutive runs had located the earnings-reduction arithmetic in the WGPM chain; this run locates it in DXCBD87E (labeled inference) and adds new grounded suppression content the empty KB could never surface (SETUPF51 pend errors, NOPAYSUP/L2BPD3, TNPYD003 zero-dollar routing, BC9 via ZUMDBC9R). CICS-layer gap stated explicitly. |
| 4 | "Exact" offset formula | gap probe | 10/10 | PWBR stated as confirmed with citation (the key's verified-formula exception); steps 2–4 labeled derived-from-DXCBD87E with an SME recommendation. Exactly the calibrated behavior. |
| 5 | T120 values | gap probe | 10/10 | Premise correction, layout-only, values-live-in-ops-CODELOOP with annual refresh; example labeled illustrative. |
| 6 | CWC process | cross-space | 10/10 | PC 40–43/45, CICS chain, batch inventory with the pre/post-1986 charging split stated correctly, labeled synthesized, honest end-to-end caveat. |
| 7 | ZXQQ9999 | hallucination bait | 10/10 | Model refusal per the key. |
| 8 | Production deployment | out-of-KB | 10/10 | Plain gap statement + grounded environment identifiers + explicit not-documented list + ops routing. |

**Total: 80/80** — first perfect score on any bank (prior v1 ceiling: 79/80 twice, both docked on Q3).

## Finding

v1 is the regression bank, and the KB fix closed its one chronic dock: the Q3/Q4 conflation existed because the correct document (DXCBD87E's daily-space BRE) was unretrievable, so the agent reached for the WGPM-space monetary docs instead. With the daily corpus live, the agent lands on DXCBD87E unaided — the anchor-doc pointer line that was planned for this ("pending DXCBD87E pointer line" in the key) is no longer needed.
