# Captured Quick chat DOM

Fixtures here are real captured pages from the AWS Quick chat agent, scrubbed of
tokens and PII. The Playwright selector and completion-detection tests run against
them so they never need a live authenticated session.

Recapture with `tools/recon_quick_dom.py` when the Quick UI changes. See
`docs/recon/` for the findings note and the scrub procedure.

**Nothing here may contain a bearer token, JWT, session token, SSN, or AWS account
id.** Run the scrub greps in the recon note before committing anything new.
