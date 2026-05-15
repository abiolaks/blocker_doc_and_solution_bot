## Parent PRD

`Issues/002-architecture-decision.md`

## What to build

The passive resolution detection and full multi-turn documentation flow in Teams, from detecting a "fixed it" signal through to approving and committing a new knowledge base entry.

Per the ADR (§3 — Full Interaction Flow steps 5–10, §5 — Document Generation):

**Passive Resolution Detection:**
- Bot monitors threads it is involved in (threads where a no-match was returned)
- Detects resolution signals: "fixed it", "sorted", "turns out it was…", "resolved", "works now", etc.
- On detection, activates the documentation flow

**Documentation Flow (multi-turn):**
1. Bot asks: *"What was the error?"* → user replies
2. Bot asks: *"What was the solution?"* → user replies
3. Bot asks: *"Which project?"* → user replies
4. Bot calls Groq doc generation (008) with the collected answers
5. Bot posts the generated Markdown preview in Teams with an approve/decline prompt
6. User approves → bot commits to GitHub (009) and triggers incremental FAISS update (010)
7. User declines → bot discards and cleans up session state

Uses conversation state management (007) to track progress through the multi-turn flow. Uses Azure Table Storage session key `user_id + thread_id`.

## Acceptance criteria

- [ ] Bot detects resolution signals from thread messages where it previously returned no-match
- [ ] Resolution detection is case-insensitive and matches the key phrases from the ADR
- [ ] Documentation flow asks exactly 3 questions in order (error, solution, project)
- [ ] Session state correctly tracks which question the user is on across multiple messages
- [ ] Generated Markdown preview is posted with an approval prompt (e.g., 👍/👎 reactions or "approve"/"decline" buttons)
- [ ] On approval: document is committed to GitHub, FAISS index is updated, session state is cleared
- [ ] On decline: session state is cleared, no commit is made
- [ ] Incomplete flows expire after 24 hours per session state TTL
- [ ] Bot does not re-trigger the flow for the same thread after completion or decline

## Blocked by

- Blocked by `Issues/008-groq-doc-generation.md` (needs doc generation endpoint)
- Blocked by `Issues/007-conversation-state.md` (needs session state for multi-turn tracking)
- Blocked by `Issues/011-teams-bot-search-trigger.md` (needs Teams bot presence in channel)

## User stories addressed

- PRD §3 — Full Interaction Flow (steps 5–10)
- PRD §3 — Passive resolution detection trigger
- PRD §5 — Document Generation (Groq-powered, template-enforced)
- PRD §8 — Conversation State Management (multi-turn flow state)
