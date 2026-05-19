## Parent PRD

`002-architecture-decision.md`

## What to build

Log all search queries and document commits to an Azure Table Storage `analytics` table for post-launch metrics tracking.

Per the ADR (§14 — Analytics & Success Metrics):

**Log on every search query:**
- `timestamp` — ISO 8601
- `event_type` — `"search"`
- `user` — Teams user ID or name
- `query` — the search query text
- `match_tier` — `"match"`, `"related"`, or `"no_match"`
- `result_path` — GitHub file path if matched/related, `null` if no match

**Log on every document commit:**
- `timestamp` — ISO 8601
- `event_type` — `"commit"`
- `user` — Teams user ID or name (the approver)
- `project` — project folder name
- `doc_path` — committed file path on GitHub

**30-Day Post-Launch Targets (for later review):**
- ≥ 20 search queries via bot
- ≥ 8 new documents committed via bot
- ≥ 40% search match rate

Export and review via direct Azure Table Storage query or Azure Portal Storage Explorer.

## Acceptance criteria

- [ ] Every `/search` call writes a row to the `analytics` Table Storage table with all fields populated
- [ ] Every `/save` call writes a row to the `analytics` Table Storage table with all fields populated
- [ ] Rows include correct timestamps in ISO 8601 format
- [ ] Analytics logging does not block the response to the user (fire-and-forget or async)
- [ ] Table can be queried to compute search match rate and document commit count

## Blocked by

- Blocked by `Issues/004-fastapi-search-endpoint.md` (logging is instrumented in search and save endpoints)

## User stories addressed

- PRD §14 — Analytics & Success Metrics
