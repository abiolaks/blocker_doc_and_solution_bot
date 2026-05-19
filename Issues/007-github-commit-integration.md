## Parent PRD

`002-architecture-decision.md`

## What to build

An endpoint and module that commits approved Markdown documents to the GitHub knowledge base, following the folder structure and naming convention.

Per the ADR (§6 — Knowledge Base Structure, §3 — Full Interaction Flow step 10):

**Module:** `commit_document(project: str, title_slug: str, markdown_content: str) → str`

- Generates filename: `YYYY-MM-DD-<title_slug>.md`
- Constructs path: `knowledge-base/<project>/<filename>`
- Commits via GitHub API (Contents API: PUT) using the PAT from env var
- Commit message: `docs: add <title_slug> for <project>`
- Commits directly to `main` — no PR workflow (Teams approval is the human-in-the-loop gate)
- Returns the GitHub URL to the committed file

**Endpoint: POST /save** (body: `{"project": "...", "title_slug": "...", "markdown": "..."}`) → `{"url": "https://github.com/...", "path": "..."}`

## Acceptance criteria

- [ ] `commit_document()` creates a file at the correct path on GitHub via the Contents API
- [ ] Filename follows `YYYY-MM-DD-short-slug.md` convention with the current date
- [ ] Commit is made directly to `main` branch
- [ ] Returns the GitHub URL of the committed file
- [ ] Handles errors gracefully (e.g., file already exists → appropriate error response)
- [ ] `/save` endpoint callable via `curl`
- [ ] GitHub PAT has `contents: write` scope on the repo only

## Blocked by

- Blocked by `Issues/004-fastapi-search-endpoint.md` (extends the same FastAPI app)

## User stories addressed

- PRD §6 — Knowledge Base Structure, GitHub Commit Strategy
- PRD §3 — Full Interaction Flow (step 10)
