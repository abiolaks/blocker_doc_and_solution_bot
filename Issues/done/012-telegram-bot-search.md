## Parent Issue

`Issues/009-teams-bot-search-trigger.md` — temporary stand-in while waiting for Teams IT approval.

## What to build

Telegram bot as a parallel UI layer for search and interaction, using the same core API modules. This proves the system works end-to-end while Teams registration is pending.

### Registration (manual, one-time HITL)
- Create a bot via [@BotFather](https://t.me/BotFather)
- Get the bot token
- Set the webhook to `https://<function-url>/api/telegram/webhook`

### Bot logic

Uses FastAPI endpoint reusing existing modules:
- **Search:** Same `search_and_resolve` from `search_api.search`
- **State:** Same session store from `conversation_state.session_store`
- **No external dependencies** beyond `httpx` (already in use) and `fastapi` (already in use)

Flow:
1. Telegram sends update → POST `/telegram/webhook`
2. Extract message text from the update body
3. Search FAISS index via `search_and_resolve`
4. Reply with tiered result via Telegram Bot API (`sendMessage`)
5. For no-match, store chat_id in conversation state for future resolution detection

Three-tier response:
- Match (>0.85): `"Found a match — here's the fix: [link]"`
- Related (0.5–0.85): `"Found something related that might help: [link] — not an exact match"`
- No match (<0.5): `"Nothing in the knowledge base for this one — I'll watch this thread"`

### Design decisions

- Telegram is a UI layer only — no search or state logic lives in the Telegram module
- Token stored in env var `TELEGRAM_BOT_TOKEN`
- Webhook auto-registers on startup (when `TELEGRAM_BOT_TOKEN` is set)
- Same `/save` flow works if triggered verbally — user can type `@bot save` or `/save` command

## Acceptance criteria

- [ ] Bot responds to direct messages and group mentions with search results
- [ ] Three-tier response messages match the ADR wording
- [ ] No-match conversations are stored in session state
- [ ] Existing search and save endpoints continue to work unchanged
- [ ] Webhook auto-registers on app startup

## Blocked by

- None — blocked by issues 004 and 005, both complete.

## Not in scope

- Docker file UX — plain text replies only
- `/save` trigger via Telegram (can be added later)
