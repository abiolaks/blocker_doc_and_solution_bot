## Parent PRD

`002-architecture-decision.md`

## What to build

Azure Table Storage-backed conversation state management that maintains multi-turn documentation flow state across stateless Azure Function invocations.

Per the ADR (§8 — Conversation State Management):

- Storage: Azure Table Storage
- Session key: composite `user_id + thread_id`
- State fields: current step in doc flow (e.g., `awaiting_error`, `awaiting_solution`, `awaiting_project`, `awaiting_approval`), collected answers so far, metadata (author, timestamp)
- Expiry: 24 hours — stale incomplete flows auto-expire (enforced via TTL or periodic cleanup)
- Purpose: enables the bot to ask 3 sequential questions without losing context between Function invocations

Expose helper functions:
- `get_session(user_id, thread_id)` → session dict or None
- `create_or_update_session(user_id, thread_id, state)` → void
- `delete_session(user_id, thread_id)` → void

These will be called by the documentation flow (012) and the Teams middleware (011).

## Acceptance criteria

- [ ] Session ID is a deterministic composite of `user_id + thread_id`
- [ ] Sessions persist across multiple HTTP calls (create, retrieve, update, retrieve again)
- [ ] Sessions older than 24 hours are either ignored or cleaned up
- [ ] Helper functions work correctly against live Azure Table Storage
- [ ] Unit tests cover session create/retrieve/update/expire paths

## Blocked by

- Blocked by `Issues/002-azure-infrastructure.md` (needs Table Storage)

## User stories addressed

- PRD §8 — Conversation State Management
- PRD §3 — Full Interaction Flow (steps 6–10 require state across turns)
