## Parent PRD

`Issues/002-architecture-decision.md`

## What to build

A document generation module that takes a user's Q&A responses and produces structured Markdown following the enforced template, powered by Groq `llama-3.1-8b-instant`.

Per the ADR (§5 — Document Generation, §3 — Full Interaction Flow steps 7–8):

**Module:** `generate_document(answers: dict) → str`

- Input: `{"error": "...", "solution": "...", "project": "..."}`
- Calls Groq `llama-3.1-8b-instant` with a system prompt that enforces the Markdown template:
  ```markdown
  # Title (generated from error)
  ## Problem
  ## Root Cause
  ## Solution
  ## Environment
  ## Tags
  ## Metadata
  ```
- Returns the generated Markdown string

**Abstraction requirement (§5):** All LLM calls must be wrapped behind this single function so the provider can be swapped (e.g., to `gpt-4o-mini`) with a one-line config change.

Expose a `/generate-doc` HTTP endpoint (POST, accepts `{"error": "...", "solution": "...", "project": "..."}`, returns `{"markdown": "..."}`) for testing and for the Teams flow (012) to call.

## Acceptance criteria

- [ ] `generate_document()` function produces valid Markdown following the template
- [ ] Generated doc includes all required sections (Title, Problem, Root Cause, Solution, Environment, Tags, Metadata)
- [ ] Title is auto-generated from the error description (not a static placeholder)
- [ ] Tags are inferred from content (not empty)
- [ ] Groq API key is read from environment variable, not hardcoded
- [ ] LLM provider is abstracted — swapping to OpenAI requires changing only one config value
- [ ] `/generate-doc` endpoint is callable via `curl` and returns valid JSON with the Markdown string
- [ ] Tested with at least 3 varied blocker scenarios (different error types, projects)

## Blocked by

- Blocked by `Issues/006-fastapi-search-endpoint.md` (extends the same FastAPI app)

## User stories addressed

- PRD §5 — Document Generation
- PRD §3 — Full Interaction Flow (step 8)
