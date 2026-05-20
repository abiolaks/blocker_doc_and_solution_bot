## Parent PRD

`002-architecture-decision.md`

## What to build

The core FastAPI application with a `/search` endpoint, deployed to Azure Functions. This is the Phase 1 exit criterion.

Per the ADR (§4 — Search & Matching, §7 — Search Flow):

**Startup (cold start per Function invocation):**
- Download `faiss.index` and `index_map.json` from Azure Blob Storage
- Load FAISS index into memory

**POST /search (body: `{"query": "..."}`):**
1. Embed the query string via OpenAI `text-embedding-3-small`
2. Search the FAISS index for nearest neighbors
3. Use `index_map.json` to resolve FAISS IDs → GitHub file paths
4. Fetch the Markdown file content from GitHub for each match
5. Return a JSON response with tiered results:
   - Score > 0.85 → `{"tier": "match", "score": X, "path": "...", "content": "..."}`
   - Score 0.5–0.85 → `{"tier": "related", "score": X, "path": "...", "content": "..."}`
   - Score < 0.5 → `{"tier": "no_match"}`
   - Return only top-N results (e.g., top 3)

Wrap the FastAPI app using `azure-functions` Python worker for HTTP trigger.

**Per ADR §13:** Teams is a pluggable UI layer — the FastAPI core must be fully testable via `curl` without Teams.

## Acceptance criteria

- [ ] FastAPI app runs locally and responds to `curl POST /search` with a valid JSON response
- [ ] Query is embedded via OpenAI, FAISS search returns integer IDs and scores
- [ ] `index_map.json` resolves IDs to GitHub paths correctly
- [ ] Tiered response follows the three-threshold logic (>0.85 match, 0.5–0.85 related, <0.5 no_match)
- [ ] Deployed to Azure Functions and reachable at the Function URL
- [ ] Cold start downloads FAISS files from Blob Storage correctly
- [ ] `curl` against the deployed endpoint returns a meaningful tiered result for a known seed document query

## Blocked by

- Blocked by `Issues/002-azure-infrastructure.md` (needs Functions, Blob Storage, OpenAI key)
- Blocked by `Issues/003-faiss-index-builder.md` (needs FAISS index in Blob Storage to search)

## User stories addressed

- PRD §4 — Search & Matching (full search flow)
- PRD §7 — FAISS Persistence & Index Mapping (search flow)
- PRD §13 — Teams Integration & IT Dependency (API testable without Teams)
- PRD §15 — Phase 1 exit criterion: "curl request against the endpoint returns a meaningful tiered result"
