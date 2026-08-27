# Quick chat DOM reconnaissance

Status: **COMPLETE** — captured 2026-08-27 against the live agent.
Verdict: **`playwright transport viable as designed`.**

Quick is Amazon Q Business components (`qbiz-*`) embedded in QuickSuite. The
testids are semantic and stable-looking, which is better than this spike assumed.

## Selectors

| Purpose | Selector | Stable? | Notes |
|---|---|---|---|
| Message input | `[data-testid="qbiz-components-prompt-textarea"]` | yes | single `<textarea>`, no aria-label |
| Thread container | `[data-testid="chat-panel-conversation-thread-container"]` | yes | also carries `data-conversation-id` |
| User turn | `[data-testid="user-chat-message-container"]` | yes | one per question asked |
| Agent turn | `[data-testid="ai-chat-message-container"]` | yes | one per answer; `innerText` is the answer |
| **Completion signal** | `[data-testid="qbiz-component-ai-message-footer"]` | yes | **one per COMPLETED answer** |
| Citations | `[data-testid="citation-reference"]` | yes | 11 on the captured pair |
| Sources control | `[data-testid="source-list-button"]` | yes | |
| Model chip | `[data-testid="qbiz-model-selection-chip"]` | yes | read `"Advanced"` — snapshot it |
| Agent selector | `[data-testid="qbiz-component-chat-experience-agent-selector-wrapper"]` | yes | how to switch agents |
| Data boundary chip | `[data-testid="qbiz-bounded-data-boundary-chip"]` | yes | |

**Do NOT use `id="base-ui-:rNN:"`.** React-generated and churning: of 55 button ids
while idle and 63 when finished, only 51 were common — 16 changed within one session.

## Streaming completion

- **Signal used: count `[data-testid="qbiz-component-ai-message-footer"]` and wait
  until it equals the number of questions asked.** The footer (like / dislike / copy)
  renders only once a message is complete. Verified: 2 questions produced exactly 2
  footers.
- Corroborating signal: a `div[role="status"]` appears with the literal text
  `"New message from Engineering Onboarding Specialist"`. Doubles as confirmation
  that the intended agent answered, which matters because the agent id is absent
  from the DOM.
- Verified against a long answer: **yes** — 4,846 characters, multiple markdown
  tables, 57 code blocks, decision cards.
- **`aria-busy` is unusable**: zero occurrences at every capture point.
- A stop-button was not captured (we sampled idle and finished, not mid-stream), so
  the footer count is the primary signal rather than a control disappearing. This is
  preferable anyway: it is a positive per-message signal, not the absence of a thing.

## Conversation addressability

- Earlier turns remain readable: both turns present with full text after scrolling.
- Answer text is **not** virtualised or truncated — `innerText` on the agent turn
  yields the whole answer, tables and code blocks included.
- All seven spot-checked scorer terms were recovered from the extracted text,
  including `ACC2528` and `CHECKS.ISSUED` which live inside markdown tables.

## conversation_id

`data-conversation-id` on the thread container. Captured value was a real UUID.
This matters because the 28 migrated legacy runs already carry a `conversation_id`,
so the harness can keep populating that column.

## Entry state

- The landing URL opens with the default agent already active in a panel — no agent
  list to navigate.
- **Run state is NOT URL-addressable.** The URL was byte-identical before and after
  arranging the chat, and is the auth redirect URL
  (`/start/home?redirect_uri=...&isauthcode=true`). So after a lost session the
  transport cannot resume by URL; it must click its way back.
- Agent id (`093ac4e3-…`) is absent from the DOM. Identify the agent by the
  `role="status"` announcement text or the agent-selector label, not by id.

## Fixtures

Raw captures are **gitignored**. They contain AWS account ids and a federated
identity ARN including the operator's email
(`arn:aws:ds:…:federated/iam/…:…@dol.nj.gov`). No JWTs (zero `eyJ` strings) and no
SSNs were present, but account ids and a named identity must not enter the repo.

Committed instead: `tests/fixtures/quick/sanitized_conversation_complete.html`
(12 KB, from 1.1 MB raw). Structure and answer text are real; account data is
removed and the conversation id is a placeholder. Verified it supports the same
selector extraction and completion detection.

**Fixture tests must load with `java_script_enabled=False`.** The live page is a
React SPA; on re-mount from `file://` its scripts wipe the captured markup and every
selector returns empty. This cost a false-negative pass during the spike.

## Follow-ups for Plan 2

1. **Use `launch_persistent_context` with a profile directory.** Authentication
   happened inside the Playwright-launched browser this run, so the session died
   with the script. A persistent profile avoids re-authenticating every run.
2. Detect the auth redirect (`isauthcode=true` / `/start/home?redirect_uri=`) and
   abort the run as `incomplete` rather than scraping a login page.
3. Suggested-question chips (`merlin-questionbar-container`, `merlin-auto-q-container`,
   `qbiz-components-quick-starters-card-*`) are clickable and could be hit
   accidentally. The quick-starter cards vanish after the first message, giving a
   usable "conversation has started" signal.
4. Answers can contain interactive decision cards
   (`qbiz-components-decision-card`, `decision-card-option-*`). Decide whether the
   transport ever interacts with them; for scoring it should not.
5. Four questions carry `after` dependencies (v3-Q2→Q1, v3-Q5→Q4, v3-Q7→Q6,
   v4-Q6→Q5) and require one continuous conversation. Confirmed feasible: both turns
   stayed addressable in a single thread.
