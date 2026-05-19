## Parent PRD

`002-architecture-decision.md`

## What to build

Incremental update of the FAISS index every time a new document is committed to the knowledge base. This ensures the search index stays current without requiring a full rebuild.

Per the ADR (§7 — Index Update Strategy):

- After a successful document commit (009), the flow triggers an incremental update:
  1. Embed the new document content via OpenAI `text-embedding-3-small`
  2. Add the embedding vector to the existing FAISS index (loaded from Blob Storage)
  3. Append the new mapping entry to `index_map.json` (next integer ID → GitHub file path)
  4. Save updated `faiss.index` and `index_map.json` back to Azure Blob Storage
- This runs synchronously as part of the `/save` flow (or as a chained call)

**Design note:** FAISS `IndexFlatIP` or `IndexFlatL2` supports `add()` for incremental insertion. Use this rather than rebuilding the index from scratch.

## Acceptance criteria

- [ ] After saving a document via `/save`, the document is searchable via `/search` without a full index rebuild
- [ ] `faiss.index` and `index_map.json` in Blob Storage reflect the new document after the update
- [ ] The new FAISS ID in `index_map.json` maps to the correct newly-committed file path
- [ ] Incremental update does not corrupt existing entries (existing searches still return correct results)
- [ ] Concurrent writes are safe (or explicitly noted as not handled in MVP)

## Blocked by

- Blocked by `Issues/003-faiss-index-builder.md` (needs the FAISS index format and Blob Storage pattern)
- Blocked by `Issues/007-github-commit-integration.md` (triggered by document commit)

## User stories addressed

- PRD §7 — Index Update Strategy (incremental update)
- PRD §3 — Full Interaction Flow (step 10: "updates FAISS index")
