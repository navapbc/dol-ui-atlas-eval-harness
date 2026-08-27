# Quick chat DOM reconnaissance

Status: **NOT YET RUN** — needs a human at the keyboard for Identity Center SSO.

Captured with `tools/recon_quick_dom.py`. Fixture: `tests/fixtures/quick/conversation_complete.html`.

## How to run it

```bash
.venv/bin/python tools/recon_quick_dom.py \
  --url "https://us-east-1.quicksight.aws.amazon.com/sn/account/njuimod/start/agents"
```

That URL lands directly on the Quick page with the default chat agent already
open, in a panel rather than full screen. There is no per-agent deep link, but no
click-through to a list is needed either. The script prompts three times: at the
landing state, once the chat is in the state a scored run would use, and after the
last answer finishes.

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

## Entry state (no deep link, but no list to navigate)

The landing URL opens with the default chat agent already active in a panel.

- Is the default agent the one under test (Engineering Onboarding Specialist)? If
  not, how is it switched, and is the switch addressable by URL?
- Is the agent id (`093ac4e3-0712-481e-af95-9ddc5e4fc734`) present anywhere in the DOM?
- Is there an expand / full-screen control, and do selectors differ between the
  panel and expanded layouts? A scored run must always start from one layout.
- Does the URL change at all between landing and run-ready state? If not, the
  transport must reproduce the state by clicking, and cannot resume by URL after a
  lost session.

Note this affects the UI transport ONLY. `snapshot()` reads agent and space config
through the read-only `aws quicksight` control-plane calls, which are unaffected.

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
