# Support Bot — Knowledge Base & Documentation Assistant

A lightweight internal Support Bot for the Data Science team, integrated with Microsoft Teams and backed by a GitHub-based knowledge base. Lets team members search past bugs and fixes, and automatically documents new blockers through a conversational flow.

## Design Principles

- **Low friction** — minimal input required from users
- **Human-in-the-loop** — users approve before anything is saved
- **GitHub as single source of truth** — all knowledge base entries are Markdown files in this repo
- **Internal first** — searches internal knowledge before any external fallback
- **Open-source and cost-effective** — no mandatory paid services

## Architecture

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

| Component | Technology |
|---|---|
| Interface | Microsoft Teams (Azure Bot Service) |
| Backend | Azure Functions (Python) |
| Core API | FastAPI |
| Conversation state | Azure Table Storage |
| Vector index persistence | Azure Blob Storage |
| Vector search | FAISS |
| Embeddings | OpenAI `text-embedding-3-small` |
| Document generation | Groq `llama-3.1-8b-instant` |
| Knowledge base | GitHub repository (Markdown files) |

## Project Structure

```
blocker_doc_and_solution_bot/
├── CLAUDE.md                  # Project instructions for AI coding agents
├── README.md                  # This file
├── Issues/                    # Design docs and task breakdown
│   ├── 001-problem-brief.md           # Original proposal
│   ├── 002-architecture-decision.md   # Architecture Decision Record (ADR)
│   ├── 003-repo-structure-seed-kb.md  # AFK — Seed knowledge base
│   ├── 004-azure-infrastructure.md    # HITL — Provision Azure resources
│   ├── 005-faiss-index-builder.md     # AFK — Build + upload FAISS index
│   ├── 006-fastapi-search-endpoint.md # AFK — Search endpoint (Phase 1 exit)
│   ├── 007-conversation-state.md      # AFK — Table Storage sessions
│   ├── 008-groq-doc-generation.md     # AFK — LLM-powered doc generation
│   ├── 009-github-commit-integration.md # AFK — Commit docs to GitHub
│   ├── 010-incremental-faiss-update.md  # AFK — Incremental index updates
│   ├── 011-teams-bot-search-trigger.md  # HITL — Teams bot registration
│   ├── 012-resolution-detection-doc-flow.md # AFK — Full Teams doc flow
│   ├── 013-analytics-logging.md        # AFK — Search + commit analytics
│   └── done/                           # Completed issues
├── ralph/                     # Ralph AI agent loop configuration
│   ├── prompt.md              # Loop instructions (task selection, TDD, commit rules)
│   ├── once.sh                # Run one AFK task at a time
│   └── afk.sh                 # Autonomous loop — run N iterations
└── knowledge-base/            # (to be created — 003)
    └── <project-name>/
        └── YYYY-MM-DD-short-slug.md
```

## Knowledge Base Document Template

All saved issues follow this enforced Markdown structure:

```markdown
# Title
Short issue summary

## Problem
Error or unexpected behavior

## Root Cause
Plain-language explanation

## Solution
Steps and code snippets

## Environment
Tools, versions, dependencies

## Tags
Relevant keywords

## Metadata
Author, date, project
```

## Implementation Phases

### Phase 1 — Core API (no Teams)
- GitHub repo with `/knowledge-base/` folder structure
- 10–15 seeded documents
- FAISS index built and stored in Azure Blob Storage
- FastAPI search endpoint deployed to Azure Functions
- **Done when:** `curl` returns a meaningful tiered search result

### Phase 2 — Teams Integration & Documentation Flow
- Azure Bot Service registration (IT approval required)
- `@mention` search trigger in `#ds-blockers`
- Passive resolution detection in-thread
- Multi-turn documentation flow with Groq-powered Markdown generation
- GitHub commit and incremental FAISS index updates
- Analytics logging

### Phase 3 — Enhancements (future)
- Bot-assisted document flagging and corrections
- Failed index update retry queue
- Screenshot/log attachment support
- External AI fallback for zero-match queries

## Current Status

- [x] Problem brief and architecture decisions finalized
- [x] 11 issues created (9 AFK, 2 HITL) from the ADR
- [x] Ralph autonomous loop configured (`ralph/prompt.md`, `ralph/afk.sh`)
- [ ] 004 — Azure Infrastructure (HITL — next action)
- [ ] 003 — Seed knowledge base (AFK — can run now)
- [ ] Remaining AFK issues (blocked until 004 complete)

## Cost

| Service | Est. monthly cost |
|---|---|
| Azure Functions (Consumption) | Free tier / <$1 |
| Azure Blob Storage | <$0.01 |
| Azure Table Storage | <$0.01 |
| OpenAI `text-embedding-3-small` | <$0.01 |
| Groq `llama-3.1-8b-instant` | Free tier |
| **Total** | **<$1/month** |

## Quick Start (Ralph Loop)

```bash
# Run one AFK task
bash ralph/once.sh

# Run autonomous loop (up to 10 tasks)
bash ralph/afk.sh 10
```
