## Parent PRD

`architecture-decision.md`

## What to build

Provision all Azure resources required by the Support Bot backend, as defined in the ADR (§9 — Infrastructure Stack):

- **Azure Functions** (Python) — hosts the FastAPI core API and all endpoints
- **Azure Blob Storage** — persists `faiss.index` and `index_map.json` for vector search
- **Azure Table Storage** — persists conversation session state and analytics rows

Configure all environment variables on the Function App:

- `GITHUB_PAT` — personal access token scoped to the KB repo with `contents: write`
- `OPENAI_API_KEY` — for `text-embedding-3-small`
- `GROQ_API_KEY` — for `llama-3.1-8b-instant`
- `AZURE_STORAGE_CONNECTION_STRING` — for Blob and Table access

## Acceptance criteria

- [ ] Azure Function App (Python, Consumption or Flex Consumption) provisioned and running
- [ ] Blob Storage account with a container created for FAISS files
- [ ] Table Storage with tables for `sessions` and `analytics` (or created on first use)
- [ ] All four environment variables set on the Function App
- [ ] GitHub PAT has `contents: write` scope on the knowledge base repo only
- [ ] Resources can be listed via Azure CLI or portal

## Blocked by

None — can start immediately (but 003 should run in parallel since 005 needs both)

## User stories addressed

- PRD §9 — Infrastructure Stack
- PRD §7 — FAISS Persistence & Index Mapping
- PRD §8 — Conversation State Management
- PRD §6 — GitHub Commits Strategy (PAT setup)
- PRD §14 — Analytics (Table Storage table)
