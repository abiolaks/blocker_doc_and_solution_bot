# CLAUDE.md

Project context and agent rules for coding agents (pi, Claude Code) working in this repo.

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

## Conversational Style

- Keep answers short and concise
- No emojis in commits, issues, PR comments, or code
- No fluff or cheerful filler text
- Technical prose only, be kind but direct ("Thanks @user" not "Thanks so much @user!")

## Code Quality

- Read files in full before making wide-ranging changes
- Use Python type hints everywhere; avoid `Any` from `typing`
- Single-line helper functions with a single call site are forbidden — inline them
- No dynamic imports (`importlib.import_module`, `__import__`) — use standard top-level imports
- Never remove or downgrade code to fix type errors; fix the actual issue
- Always ask before removing functionality that appears intentional
- Never hardcode configuration values — use environment variables or a config file

## Commands

- After code changes: `ruff check . && ruff format --check .` (once configured). Fix all errors before committing.
- Never run the dev server or bot unless the user explicitly asks
- Only run tests if the user instructs: `pytest test/specific_test.py -v`
- If you create or modify a test file, run it and iterate until it passes

## Git Rules

- Never commit unless the user asks
- Only commit files you changed in this session
- Never use `git add -A` or `git add .` — always `git add <specific-file>`
- Before committing, run `git status` and verify you're only staging your files
- Never run: `git reset --hard`, `git checkout .`, `git clean -fd`, `git stash`
- If rebase conflicts occur in files you didn't modify, abort and ask the user
- Include `fixes #<number>` or `closes #<number>` in commit messages when applicable

## PR Workflow

- Analyze PRs without pulling locally first
- If user approves: create feature branch, pull PR, rebase on main, apply adjustments, commit, merge into main, push, close PR, leave a concise comment
- Never open PRs yourself — work in feature branches until ready, then merge and push
