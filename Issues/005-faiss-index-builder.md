## Parent PRD

`Issues/002-architecture-decision.md`

## What to build

A Python script (or Azure Function) that builds the initial FAISS vector index from the seed knowledge base and uploads both the index and mapping file to Azure Blob Storage.

Per the ADR (§7 — FAISS Persistence & Index Mapping, §4 — Search & Matching):

- Fetch all Markdown documents from `/knowledge-base/` on GitHub (clone or API)
- Embed each document using OpenAI `text-embedding-3-small`
- Build a FAISS index from the embeddings
- Create `index_map.json` mapping FAISS integer IDs → GitHub file paths (e.g., `"0": "knowledge-base/project-alpha/2026-05-04-sklearn-error.md"`)
- Upload `faiss.index` (binary) and `index_map.json` to Azure Blob Storage

This script is also the basis for the future manual full-rebuild operation.

## Acceptance criteria

- [ ] Script successfully fetches all seed documents from the GitHub KB
- [ ] Each document is embedded via `text-embedding-3-small`
- [ ] FAISS index is built and contains one vector per document
- [ ] `index_map.json` correctly maps every FAISS ID to its source file path
- [ ] Both files uploaded to Azure Blob Storage and downloadable for verification
- [ ] Script can be re-run idempotently (rebuilds from scratch)

## Blocked by

- Blocked by `Issues/003-repo-structure-seed-kb.md` (needs seed documents to embed)
- Blocked by `Issues/004-azure-infrastructure.md` (needs Blob Storage and OpenAI API key)

## User stories addressed

- PRD §7 — FAISS Persistence & Index Mapping
- PRD §4 — Search & Matching (embedding model, vector store)
- PRD §10 — Cold Start & Seeding (index build from seed docs)
