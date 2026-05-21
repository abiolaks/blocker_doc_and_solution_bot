""""""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx
from azure.data.tables import TableClient

from blocker_doc_and_solution_bot.conversation_state.session_store import (
    create_or_update_session,
)
from blocker_doc_and_solution_bot.search_api.search import search_and_resolve


def _format_reply(results: list[dict[str, str | float]]) -> str:
    """Build the tiered reply text from search results.

    Takes the best result and formats per the ADR:
    - match (>0.85): "Found a match — here's the fix: [path]"
    - related (0.5–0.85): "Found something related that might help: [path] — not an exact match"
    - no_match (<0.5): "Nothing in the knowledge base for this one — I'll watch this thread"
    """
    if not results:
        return "Nothing in the knowledge base for this one — I'll watch this thread"

    best = results[0]
    tier = best["tier"]
    path = str(best["path"])

    if tier == "match":
        return f"Found a match — here's the fix: {path}"
    if tier == "related":
        return f"Found something related that might help: {path} — not an exact match"
    return "Nothing in the knowledge base for this one — I'll watch this thread"


def send_telegram_message(
    chat_id: int,
    text: str,
    *,
    bot_token: str,
    reply_to_message_id: int | None = None,
    http_client: httpx.Client | None = None,
) -> None:
    """Send a message via the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: dict[str, object] = {"chat_id": chat_id, "text": text}
    if reply_to_message_id is not None:
        payload["reply_to_message_id"] = reply_to_message_id

    client = http_client or httpx.Client()
    try:
        response = client.post(url, json=payload)
        response.raise_for_status()
    finally:
        if http_client is None:
            client.close()


def handle_telegram_update(
    update: dict[str, Any],
    *,
    bot_token: str,
    search_fn: Callable[..., object] | None = None,
    send_fn: Callable[..., None] | None = None,
    store_session_fn: Callable[..., None] | None = None,
    table_client: TableClient | None = None,
) -> None:
    """Process a Telegram webhook update: extract text, search, reply.

    search_fn(query: str) -> list[dict] — injectable for testing.
    send_fn(chat_id, text, reply_to_message_id, bot_token) — injectable for testing.
    store_session_fn(chat_id, message_id) — injectable for testing.
    """
    message = update.get("message", {})
    text: str | None = message.get("text")
    if not text:
        return

    chat_id: int = message["chat"]["id"]
    message_id: int = message["message_id"]
    user_id: str = str(message.get("from", {}).get("id", ""))

    # Run search
    raw: list[dict[str, str | float]]
    if search_fn is not None:
        raw = search_fn(text)  # type: ignore[assignment]
    else:
        from blocker_doc_and_solution_bot.search_api.app import (
            _faiss_index,
            _index_map,
            _openai_client,
        )
        from blocker_doc_and_solution_bot.search_api.search import embed_query

        if _openai_client is None or _faiss_index is None:
            send_telegram_message(
                chat_id=chat_id,
                text="Search index not loaded. Try again later.",
                bot_token=bot_token,
            )
            return

        query_vec = embed_query(text, _openai_client)
        raw = search_and_resolve(query_vec, _faiss_index, _index_map, top_k=3)

    reply = _format_reply(raw)

    if send_fn is not None:
        send_fn(chat_id=chat_id, text=reply, reply_to_message_id=message_id, bot_token=bot_token)
    else:
        send_telegram_message(
            chat_id=chat_id,
            text=reply,
            bot_token=bot_token,
            reply_to_message_id=message_id,
        )

    # For no-match, store session for future resolution detection
    best = raw[0] if raw else {"tier": "no_match"}
    if best["tier"] == "no_match":
        if store_session_fn is not None:
            store_session_fn(chat_id=chat_id, message_id=message_id)
        elif table_client is not None:
            create_or_update_session(
                user_id=user_id,
                thread_id=str(chat_id),
                state={"last_query": text},
                table_client=table_client,
            )


def register_webhook(bot_token: str, webhook_url: str) -> bool:
    """Set the Telegram bot webhook to the given URL.

    Returns True on success, False on failure.
    """
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    try:
        with httpx.Client() as client:
            response = client.post(url, json={"url": webhook_url})
            return response.status_code == 200 and response.json().get("ok", False)
    except httpx.HTTPError:
        return False
