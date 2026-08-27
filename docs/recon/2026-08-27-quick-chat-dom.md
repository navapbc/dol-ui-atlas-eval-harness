# Quick chat DOM reconnaissance

Status: **NOT YET RUN** — needs a human at the keyboard for Identity Center SSO.

Captured with `tools/recon_quick_dom.py`. Fixture: `tests/fixtures/quick/conversation_complete.html`.

## How to run it

```bash
.venv/bin/python tools/recon_quick_dom.py --url "<quick chat agent URL>"
```

A headed Chromium opens. You sign in yourself — the script never touches
credentials and never types into a password field. It prompts twice: once after
you have the chat open, once after the last answer has fully rendered.

Ask at least two questions, and make one of them long-running. Completion
detection must be exercised against a multi-paragraph streaming answer, because a
one-line reply finishes too fast to distinguish "done" from "not started".

## Scrub before committing

The dump is a real authenticated page. Run these and resolve every hit:

```bash
cd tests/fixtures/quick
grep -oiE '(bearer [a-z0-9._-]{20,}|eyJ[A-Za-z0-9._-]{30,}|x-amz-security-token|sessionToken)' conversation_complete.html | sort -u | head
grep -oE '[0-9]{3}-?[0-9]{2}-?[0-9]{4}' conversation_complete.html | sort -u | head
grep -oE 'arn:aws[^" ]{0,120}' conversation_complete.html | sort -u | head
```

No token, JWT, or SSN matches may remain. Mask account ids inside ARNs. If the page
cannot be scrubbed with confidence, do not commit it — record the selectors in the
table below instead and say so here.

## Selectors

| Purpose | Selector | Stable? | Notes |
|---|---|---|---|
| Message input | | | |
| Submit control | | | |
| Message list container | | | |
| One agent turn | | | |
| Streaming-in-progress signal | | | |

## Streaming completion

- Signal used:
- Verified against a long (multi-paragraph) answer: yes/no
- False positive observed mid-stream: yes/no
- Reliable enough for unattended runs: yes/no

## Conversation addressability

- Are earlier turns still readable after the thread scrolls?
- Is the full answer text in the DOM, or virtualised/truncated?

## conversation_id

- Where it surfaces (DOM attribute, URL, or network response):

Needed because the existing `scores.csv` records `conversation_id` per run, and
28 migrated legacy runs already carry one.

## Run-order constraint

Four questions declare an `after` dependency and must run immediately after their
target in the same conversation: v3-Q2 after v3-Q1, v3-Q5 after v3-Q4, v3-Q7 after
v3-Q6, v4-Q6 after v4-Q5. Each plants a term the next one tests, so the transport
must keep one continuous conversation and must not reorder. Note whether the UI
allows that.

## Verdict

One of:
- `playwright transport viable as designed`
- `viable with an explicit per-question settle-and-confirm step`
- `paste transport should be primary`

This verdict is the input to Plan 2 (the Quick adapter transports), which is not
written yet and is deliberately blocked on it.
