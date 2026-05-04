# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight internal **Support Bot** for the Data Science team, integrated with **Microsoft Teams** and backed by a **GitHub-based knowledge base**. The bot lets team members search past bugs and fixes, and automatically documents new blockers through a conversational flow — without requiring manual Markdown writing. The knowledge base is the GitHub repo itself; GitHub is the single source of truth.

The goal is not to replace ChatGPT, but to capture and reuse solutions already discovered by the team, with minimal friction.

## Current State

Planning and design phase — no application code written yet. All design documents live in `Issues/` numbered sequentially.

- `Issues/001-problem-brief.md` — Current proposal covering problem statement, design principles, core features, documentation standard, architecture, implementation phases, and success criteria.

## Design Principles

- **Low friction** — minimal input required from users.
- **Human-in-the-loop** — users approve before anything is saved to the knowledge base.
- **GitHub as single source of truth** — all knowledge base entries are Markdown files in this repo.
- **Internal first** — the bot searches internal knowledge before falling back to external sources.
- **Open-source and cost-effective** — no mandatory paid services.

## Planned Architecture

```
Microsoft Teams → Support Bot API → GitHub Knowledge Base → Vector Search Index
```

| Component | Technology |
|---|---|
| Interface | Microsoft Teams Bot |
| Backend API | Python (FastAPI or similar) |
| Knowledge Base | GitHub repository (Markdown files) |
| Vector Search | FAISS or Chroma (open-source) |
| LLM | Lightweight model for text structuring (optional) |

### Search Flow

User submits error/question in Teams → bot embeds query → vector similarity search over GitHub knowledge base → returns matching past issues, fixes, and a link to the GitHub doc. If no match, bot explicitly says so.

### Documentation Flow

User triggers save → bot asks: *What error occurred? What was the solution? Which project?* → bot generates structured Markdown from the answers → user approves → bot commits the doc to GitHub and updates the vector index.

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

Users never write this manually — the bot generates and commits it.

## Implementation Phases

- **Phase 1 (MVP)** — GitHub knowledge base repo, documentation template, seed with existing issues, basic search.
- **Phase 2** — Conversational save-fix flow in Teams, automatic Markdown generation and GitHub commit, vector index updates.
- **Phase 3 (Optional)** — Screenshot/log support, common-issue analytics, optional external AI fallback.

## Planning Document Convention

Design and planning docs go in `Issues/` with sequential three-digit prefixes (e.g., `002-architecture-decision.md`).
