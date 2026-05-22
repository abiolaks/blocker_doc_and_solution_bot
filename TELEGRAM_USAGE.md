# Using the Support Bot on Telegram

How team members search past blockers and document new ones via the Telegram bot.

## TL;DR

| Goal | What to type | What the bot does |
|---|---|---|
| Search the knowledge base | Just type your error / question | Returns the closest match with a GitHub link |
| Document a new blocker | Send the query first → after you fix it, reply with "fixed it" / "solved" / "figured it out" | Walks you through error → solution → project → approval, then commits to GitHub |
| Approve a generated doc | `approve` / `yes` / `ok` | Commits to GitHub, updates the search index |
| Reject a generated doc | `decline` / `no` / `cancel` | Discards, no commit |
| Cancel mid-flow (any question) | `cancel` / `stop` / `abort` / `nevermind` / `quit` | Aborts immediately, no commit |

**The bot has no slash commands.** Whatever you type is interpreted based on conversational context.

## Finding the bot

The Telegram bot lives at the handle configured by whoever set it up via @BotFather. Open it in Telegram (`https://t.me/<bot_username>`), tap **Start**, and the bot is ready for you in a private chat.

The bot's webhook auto-registers on the Azure Function's first start; you don't need to do anything to "wake" it.

## 1. Searching for a known solution

Send any message describing your error or question. There's no prefix, no command — just describe the problem.

```
You:  docker login fails with permission denied
Bot:  Found a match — here's the fix: https://github.com/abiolaks/blocker_doc_and_solution_bot/blob/main/Knowledge_base/IVR_pipeline/Docker_login.md
```

The bot embeds your query, runs vector similarity over the FAISS index of the GitHub knowledge base, and returns the best hit. The reply phrasing depends on how confident the match is:

| Similarity score | Tier | Bot reply |
|---|---|---|
| `> 0.85` | match | "Found a match — here's the fix: \<url\>" |
| `0.5 – 0.85` | related | "Found something related that might help: \<url\> — not an exact match" |
| `< 0.5` | no_match | "Nothing in the knowledge base for this one — I'll watch this thread" |

"Not an exact match" means: the doc is plausibly relevant but the embedding isn't confident it's a direct hit. Open the link and judge for yourself.

"I'll watch this thread" means: the bot stored your query in a session for the next 24 hours. If you tell it later that you fixed the problem, it will offer to document it (next section).

## 2. Documenting a new blocker

You don't write Markdown. The bot walks you through it.

### Step 1 — Trigger the documentation flow

After a `no_match` response, when you eventually fix the issue, reply with any phrase that signals resolution:

- `fixed it`
- `solved`
- `figured it out`
- `sorted`
- `resolved`
- `works now`
- `turns out`

The bot detects the resolution language (case-insensitive substring match) and starts the multi-turn flow:

```
You (earlier):  some weird error nobody's seen before
Bot:            Nothing in the knowledge base for this one — I'll watch this thread

[... time passes, you figure it out ...]

You:  fixed it
Bot:  Looks like you found a fix! Let's document it.
      What was the error or unexpected behavior?
```

### Step 2 — Three questions

The bot asks three questions, one at a time. Reply to each in plain English. The bot stores your raw answers; it does not interpret them.

```
Bot:  What was the error or unexpected behavior?
You:  docker login was failing with "Error saving credentials"

Bot:  What was the solution? What steps fixed it?
You:  removed ~/.docker/config.json and ran docker login again

Bot:  Which project or service was this related to?
You:  IVR_pipeline
```

### Step 3 — Review the generated document

After the project answer, the bot sends your three answers to Groq, which generates a structured Markdown document and returns it for review:

```
Bot:  Here's the generated knowledge base entry:

      # Failed Docker Login Due to Saved Credentials
      Short summary…

      ## Problem
      …

      ## Root Cause
      …

      ## Solution
      …

      ## Environment
      …

      ## Tags
      …

      ## Metadata
      …

      Reply 'approve' to save to GitHub or 'decline' to discard.
```

### Step 4 — Approve or decline

- **`approve`**, `yes`, or `ok` → bot commits the doc to GitHub at
  `knowledge-base/<project>/<YYYY-MM-DD>-<slug>.md` and updates the FAISS index
  in blob storage. Reply: **"Saved to the knowledge base!"**
- **`decline`**, `no`, or `cancel` → bot discards the draft and clears the session.
  Reply: **"Discarded. Nothing was saved."**

Anything else at this step is treated as if you're trying to amend (currently not supported — see "Limitations" below).

## 3. Behavior notes

### No slash commands
Unlike many Telegram bots, this one has no `/start`, `/help`, `/search`, or `/save`. Typing `/search docker error` will literally search the knowledge base for the string `/search docker error` (the slash and `search` word are part of your query). Just type the error directly.

### Session lifetime
The "I'll watch this thread" session and the doc flow session both live in Azure Table Storage with a 24-hour TTL. Walk away mid-flow and your draft expires after a day.

### Group chats
By default, Telegram's bot "privacy mode" hides most group messages from bots — they only see messages that:
- Start with a `/` command (we have none)
- @mention the bot
- Reply directly to a bot message

For the bot to be useful in a group chat without a lot of @mention noise, disable privacy mode in @BotFather:

```
@BotFather → /setprivacy → pick this bot → Disable
```

After that the bot sees every group message and searches each one. (Pros: organic UX. Cons: noisy.) If you keep privacy mode on, users will need to reply to the bot's previous message to continue any conversation.

### What gets sent where
- **Searches** — local FAISS lookup over the GitHub KB (Azure Blob)
- **Doc generation** — Groq API (`generate_document` in `doc_generator/generator.py`)
- **Commits** — GitHub Contents API using `GITHUB_PAT`
- **Index update** — incremental embed via `text-embedding-3-small` (OpenAI), then re-upload to blob

All of this happens server-side in the Azure Function. The bot only handles message routing.

## 4. Examples

### Example A — Match found

```
You:  HTTP trigger function not found after deploy
Bot:  Found a match — here's the fix:
      https://github.com/abiolaks/blocker_doc_and_solution_bot/blob/main/Knowledge_base/Real_customer_sentiment_analysis/HTTP_trigger_not_found.md
```

→ open the link, read the doc, you're done.

### Example B — Related but not exact

```
You:  spark cluster pool out of vcores
Bot:  Found something related that might help:
      https://github.com/abiolaks/blocker_doc_and_solution_bot/blob/main/Knowledge_base/Social_Media_Analytics/spark_pool_vcores.md
      — not an exact match
```

→ open the link, see if it applies. If yes, no further action. If no, treat as if it were a no-match (try fixing it; document if useful).

### Example C — No match, then resolution + document

```
You (Mon 10:14):  function app returns 503 on first invocation only
Bot (Mon 10:14):  Nothing in the knowledge base for this one — I'll watch this thread

You (Mon 11:02):  sorted, it was the cold-start lifespan handler
Bot (Mon 11:02):  Looks like you found a fix! Let's document it.
                  What was the error or unexpected behavior?

You:  function app returns 503 on first request after deploy, stops after worker warms
Bot:  What was the solution? What steps fixed it?
You:  moved FAISS index load from FastAPI lifespan to module-level eager init
Bot:  Which project or service was this related to?
You:  azure_functions
Bot:  Here's the generated knowledge base entry:
      [structured Markdown doc]
      Reply 'approve' to save to GitHub or 'decline' to discard.

You:  approve
Bot:  Saved to the knowledge base!
```

→ doc is now on GitHub at `knowledge-base/azure_functions/2026-05-22-function-app-returns-503.md` and discoverable by FAISS for future searches.

## 5. Limitations / FAQ

**Q: Can I edit a generated doc before approval?**
Not currently — only `approve` / `decline`. If the generated doc is wrong, decline and start over with better answers.

**Q: How do I cancel the conversation mid-way?**
Type `cancel`, `stop`, `abort`, `nevermind`, or `quit` (case-insensitive, exact word only) at any of the awaiting steps. The bot replies "Cancelled. Nothing saved." and clears the session. Note that "cancel my flight" or similar substrings won't trigger cancellation — the match has to be the whole message.

**Q: Can I save without going through the conversational flow?**
Not via Telegram. The HTTP API has a direct `POST /api/save` endpoint that takes pre-written Markdown, if you want to script it.

**Q: Saved doc isn't showing up when I search for it.**
Known limitation — see Issue 014 (`Issues/014-stale-in-memory-faiss-after-save.md`). The FAISS index is updated in blob storage but the worker's in-memory copy is stale until it recycles (~20–30 min idle). Cold starts pick up the new index.

**Q: The save folder convention differs from the existing KB.**
New docs land at `knowledge-base/<project>/...` (lowercase, hyphen), while existing KB is at `Knowledge_base/<project>/...` (capital, underscore). They coexist on disk; both are indexed. Cleanup is a separate concern.

**Q: How do I switch Telegram bots (e.g. dev vs prod)?**
Each environment uses a separate `TELEGRAM_BOT_TOKEN` app setting. Updating the setting and restarting the Function App causes `_initialize_state()` to re-register the webhook against the new bot token.
