# 002 — Architecture Decision Record: Support Bot

## Overview

This document captures all finalized architecture and design decisions for the Data Science Support Bot, derived from a structured design review of `001-problem-brief.md`. It supersedes any ambiguous or unresolved details in the problem brief.

---

## 1. Ownership & Team Context

| Item | Decision |
|---|---|
| Maintainer | Single DRI — project owner |
| Team size | 7 people |
| Expected blocker volume | 3–5 new blockers per week |
| Rollout strategy | Soft launch with 1 trusted teammate for 1–2 weeks before full team announcement |

---

## 2. System Architecture

```
Microsoft Teams (#ds-blockers channel)
    ↓  @mention trigger (search)
    ↓  passive resolution detection (documentation)
Azure Bot Service + Bot Framework SDK
    ↓
Azure Functions (stateless, serverless)
    ↓               ↓                    ↓
FastAPI Core    Azure Table Storage   Azure Blob Storage
    ↓           (conversation state)  (faiss.index + index_map.json)
GitHub Repo
(knowledge base)
    ↓
OpenAI Embeddings → FAISS Vector Index
    ↓
Groq llama-3.1-8b-instant (document generation)
```

### Core Principle
The FastAPI core API is **Teams-agnostic**. Teams is a UI layer that calls the same API endpoints that can also be called via curl or any other interface. This allows full development and testing before Teams bot IT approval is granted.

---

## 3. Interface & Trigger Design

| Trigger | Mechanism |
|---|---|
| Search | User explicitly `@mentions` the bot with a blocker description |
| Documentation | Bot passively monitors threads it is involved in, activates on resolution signals ("fixed it", "sorted", "turns out it was…") |
| Access scope | Channel-scoped — bot only operates in `#ds-blockers` (or equivalent designated channel) |

### Full Interaction Flow

1. User posts blocker in `#ds-blockers` and `@mentions` the bot
2. Bot embeds the full message and searches the FAISS index
3. **If match found:** Bot returns tiered result in-thread
4. **If no match:** Bot replies "Not in the knowledge base — I'll watch this thread"
5. Team discusses in thread naturally
6. User posts resolution signal → bot activates documentation flow
7. Bot asks 3 questions: *What was the error? What was the solution? Which project?*
8. Bot generates structured Markdown via Groq llama-3.1-8b-instant
9. Bot posts preview in Teams for user approval
10. User approves → bot commits to GitHub, updates FAISS index and index_map.json

---

## 4. Search & Matching

| Item | Decision |
|---|---|
| Search input | Full message content (not just error string) |
| Embedding model | OpenAI `text-embedding-3-small` |
| Vector store | FAISS |
| Match threshold — high confidence | Score > 0.85 → "Found a match — here's the fix: [link]" |
| Match threshold — related | Score 0.5–0.85 → "Found something related that might help: [link] — not an exact match" |
| Match threshold — no match | Score < 0.5 → "Nothing in the knowledge base for this one" |

---

## 5. Document Generation

| Item | Decision |
|---|---|
| LLM for MVP | Groq `llama-3.1-8b-instant` (free tier) |
| LLM for future | Swap to OpenAI `gpt-4o-mini` via one-line config change |
| Abstraction | All LLM calls wrapped behind a `generate_document(answers)` function to make provider swapping trivial |
| Template | Enforced Markdown structure (Title, Problem, Root Cause, Solution, Environment, Tags, Metadata) |

---

## 6. Knowledge Base Structure

### Folder Structure
```
/knowledge-base/
  /<project-name>/
    YYYY-MM-DD-short-slug.md
```

Example:
```
/knowledge-base/
  /project-alpha/
    2026-05-04-modulenotfounderror-sklearn.md
  /project-beta/
    2026-05-10-keyerror-user-id-pipeline.md
```

### GitHub Commit Strategy
- Bot commits **directly to `main`** on user approval in Teams
- No PR workflow — Teams approval is the human-in-the-loop gate
- Authentication via **GitHub PAT** scoped to this repo with `contents: write` permission, stored as Azure Function environment variable

---

## 7. FAISS Persistence & Index Mapping

Two files stored in **Azure Blob Storage**, loaded and saved on every Function invocation:

| File | Purpose |
|---|---|
| `faiss.index` | Binary FAISS vector index |
| `index_map.json` | Maps FAISS integer IDs to GitHub file paths |

### index_map.json structure
```json
{
  "0": "knowledge-base/project-alpha/2026-05-04-sklearn-error.md",
  "1": "knowledge-base/project-beta/2026-05-10-keyerror-pipeline.md"
}
```

### Index Update Strategy
- **Incremental update** on every new document commit — embed new doc, add to existing FAISS index, save both files back to Blob Storage
- **Full rebuild** available as a manual maintenance operation if index corruption is suspected

### Search Flow
```
Query → OpenAI embedding → FAISS search → integer IDs + scores
→ index_map.json lookup → GitHub file paths
→ fetch file content → return tiered result
```

---

## 8. Conversation State Management

| Item | Decision |
|---|---|
| Storage | Azure Table Storage |
| Session key | `user_id + thread_id` |
| State expiry | 24 hours (stale incomplete flows auto-expire) |
| Purpose | Maintain multi-turn documentation flow state across stateless Azure Function invocations |

---

## 9. Infrastructure Stack

| Component | Technology |
|---|---|
| Interface | Microsoft Teams (Azure Bot Service + Bot Framework SDK) |
| Backend | Azure Functions (Python) |
| Core API | FastAPI |
| Conversation state | Azure Table Storage |
| Vector index persistence | Azure Blob Storage |
| Vector search | FAISS |
| Embeddings | OpenAI `text-embedding-3-small` |
| Document generation | Groq `llama-3.1-8b-instant` |
| Knowledge base | GitHub repository (Markdown files) |
| GitHub auth | Personal Access Token (env variable) |

---

## 10. Cold Start & Seeding

- Knowledge base seeded with **10–15 real past blockers** before launch
- Seeding done manually by project owner and one teammate using the Markdown template
- Target: highest-frequency recurring blockers from Teams chat history, GitHub issues, and OneNote
- Goal: ≥ 40% search match rate on day one of full team launch

---

## 11. Document Corrections & Updates

| Phase | Strategy |
|---|---|
| MVP (Phase 1–2) | Manual GitHub file edits; full FAISS rebuild to re-index corrected content |
| Phase 3 | Bot-assisted flagging: `@bot this fix is wrong` → flags doc, notifies maintainer to review |

---

## 12. Failure Handling

| Phase | Strategy |
|---|---|
| MVP | Ignored — manual full index rebuild resolves any index/document desync |
| Phase 2 | Failed index updates logged to Azure Table Storage `pending_index` queue; hourly scheduled Function re-indexes queued entries |

---

## 13. Teams Integration & IT Dependency

- Teams bot requires **IT approval** for tenant registration via Azure Bot Service
- **Mitigation:** Submit IT request immediately; build and validate the full core API independently using HTTP requests while approval is pending
- Teams is a pluggable UI layer — all core logic is testable without it

---

## 14. Analytics & Success Metrics

All search queries and document commits write a row to an Azure Table Storage `analytics` table (timestamp, user, query, match tier, result path).

### 30-Day Post-Launch Targets

| Metric | Target |
|---|---|
| Search queries via bot | ≥ 20 |
| New documents committed via bot | ≥ 8 |
| Search match rate | ≥ 40% |

Review monthly via direct Azure Table Storage export.

---

## 15. Implementation Phases (Revised)

### Phase 1 — MVP (Core API, no Teams)
- GitHub repo with `/knowledge-base/` folder structure
- 10–15 seeded documents
- FAISS index built and stored in Azure Blob Storage
- FastAPI search endpoint deployed to Azure Functions
- Tiered search results via HTTP
- **Done when:** curl request against the endpoint returns a meaningful tiered result

### Phase 2 — Teams Integration & Documentation Flow
- Azure Bot Service registration (pending IT approval)
- `@mention` search trigger in `#ds-blockers`
- Passive resolution detection in-thread
- Multi-turn documentation flow with Azure Table Storage session state
- Groq-powered Markdown generation and GitHub commit
- Incremental FAISS index updates post-commit
- Analytics table logging

### Phase 3 — Enhancements (Optional)
- Bot-assisted document flagging and correction flow
- Failed index update queue and retry mechanism
- Screenshot and log attachment support
- Common-issue analytics dashboard
- Optional swap to OpenAI GPT-4o-mini for document generation
- External AI fallback for zero-match queries
