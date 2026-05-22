## Parent Issue

`Issues/done/008-incremental-faiss-update.md` — Incremental FAISS update wired into `/api/save`, but only the blob copy is refreshed.

## What to build

Fix the in-memory FAISS index on a running Function worker so that documents committed via `/api/save` (or the Telegram approval flow) are searchable on the same worker without waiting for a cold start.

## Problem

`search_api/app.py:_initialize_state()` loads `faiss.index` and `index_map.json` from blob **once** at module import, populating module-level globals `_faiss_index` and `_index_map`. The `/api/search` endpoint reads from these globals.

`/api/save` calls `add_document_to_index()` (`index_updater/updater.py`), which downloads the blob index, appends the new vector, and uploads the updated blob — but it does not touch the in-memory `_faiss_index` or `_index_map` on the worker that handled the save.

Result: a user who approves a new doc and immediately searches for the same content can get `no_match` if their search routes to the same warm worker. The document is on GitHub, the embedding is in the blob index, but the worker's in-memory copy is stale until it's recycled (FlexConsumption scales to zero after ~20-30 min of idle).

Affects: any user who saves a doc and searches in the next few minutes.

## Options considered

1. **Same-worker fix (cheapest)** — after `add_document_to_index` succeeds, also call `_faiss_index.add(vec)` and `_index_map[str(new_id)] = path` on the local module globals. Fixes the saving worker; peer workers remain stale until they recycle.
2. **TTL-based reload** — on every Nth search, or after a configurable idle period, reload the index from blob. Catches peer workers eventually.
3. **Fan-out signal** — use Azure Service Bus / Event Grid topic + a queue trigger per worker to broadcast a "reload index" event. Cleanest but adds infra.

Option 1 is recommended for now: simple, addresses the most common case (same user searching after saving), and doesn't add infra. Revisit if multi-worker scenarios become common.

### AFK (agent can do)

- In `add_document_to_index`, return the new vector so the caller can update the in-memory index.
- In `/api/save` (`search_api/app.py`), after a successful `add_document_to_index` call, append to `_faiss_index` and `_index_map`.
- Add a test that asserts `_faiss_index.ntotal` increases by 1 after `/api/save`, and that the new path is reachable via `/api/search` on the same module instance.

### HITL (user does)

- Decide whether to also implement Option 2 or 3 for cross-worker freshness (out of scope here).

## Acceptance criteria

- [ ] After a successful `/api/save` request, the in-memory `_faiss_index.ntotal` on the same worker has grown by 1.
- [ ] An immediate `/api/search` on the same worker for the saved document's content returns a `match` tier hit pointing at the new path.
- [ ] Existing tests pass; new test covers the same-worker round-trip.

## Blocked by

- None.

## Not in scope

- Cross-worker freshness (Option 2 / 3 above).
- Background sync from blob to memory.
- Index versioning / optimistic concurrency between writers.
