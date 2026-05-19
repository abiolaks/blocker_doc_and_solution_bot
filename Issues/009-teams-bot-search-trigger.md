## Parent PRD

`002-architecture-decision.md`

## What to build

Register the Microsoft Teams bot via Azure Bot Service and implement the `@mention` search trigger in the `#ds-blockers` channel.

Per the ADR (§3 — Interface & Trigger Design, §13 — Teams Integration & IT Dependency):

**Registration (HITL — requires IT approval):**
- Register a Bot Channels Registration in Azure Bot Service
- Configure Microsoft Teams as the channel
- Set the messaging endpoint to the Azure Function URL
- Submit IT request for tenant approval immediately — this may take time

**Bot logic:**
- Bot is channel-scoped to `#ds-blockers` (or equivalent designated channel)
- When a user `@mentions` the bot with a blocker description:
  1. Extract the full message text
  2. Call the FastAPI `/search` endpoint (006) with the message content
  3. Post the tiered result back in-thread:
     - Match (>0.85): `"Found a match — here's the fix: [link]"`
     - Related (0.5–0.85): `"Found something related that might help: [link] — not an exact match"`
     - No match (<0.5): `"Nothing in the knowledge base for this one — I'll watch this thread"`
  4. For no-match cases, store the thread ID in conversation state (007) to enable future resolution detection (012)

Uses Azure Bot Service SDK (Python) integrated into the Azure Function.

## Acceptance criteria

- [ ] Bot registered in Azure Bot Service with Teams channel configured
- [ ] IT approval obtained for Teams tenant registration
- [ ] Bot is added to `#ds-blockers` and responds to `@mention`
- [ ] Search results are posted as threaded replies, not new messages
- [ ] Three-tier response messages match the ADR wording
- [ ] Bot does not respond in channels other than `#ds-blockers`
- [ ] Bot can be tested with the Bot Framework Emulator before Teams is available

## Blocked by

- Blocked by `Issues/004-fastapi-search-endpoint.md` (needs the search endpoint to call)
- Blocked by `Issues/005-conversation-state.md` (needs session state for no-match thread tracking)

## User stories addressed

- PRD §3 — Interface & Trigger Design (search trigger, access scope)
- PRD §3 — Full Interaction Flow (steps 1–4)
- PRD §4 — Search & Matching (tiered response messages)
- PRD §13 — Teams Integration & IT Dependency
