"""Microsoft Teams bot — ActivityHandler for @mention search and doc flow.

Uses Bot Framework SDK to receive messages from Azure Bot Service
and respond with tiered search results from the FAISS knowledge base.

All external dependencies (OpenAI client, FAISS index, analytics table)
are injected via the constructor rather than imported directly to avoid
circular imports with the FastAPI app module.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import faiss
from azure.data.tables import TableClient
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
)
from botbuilder.core.teams import TeamsActivityHandler
from openai import OpenAI

from blocker_doc_and_solution_bot.conversation_state.session_store import (
    create_or_update_session,
)
from blocker_doc_and_solution_bot.telegram_bot.bot import _format_reply
from blocker_doc_and_solution_bot.telegram_bot.resolution import (
    DocFlowState,
    advance_doc_flow,
    handle_approval,
    is_resolution_signal,
    start_doc_flow,
)

# Pattern used by Teams to mention a bot: <at>Bot Name</at> extra text
_MENTION_PREFIX = "<at>"
_MENTION_SUFFIX = "</at>"


def _strip_mention(text: str) -> str:
    """Remove Teams @mention markup from message text.

    Teams wraps @mentions as: <at>Bot Name</at>
    Returns the text with all mention tags stripped and leading/trailing whitespace removed.
    """
    result = text
    while _MENTION_PREFIX in result and _MENTION_SUFFIX in result:
        start = result.index(_MENTION_PREFIX)
        end = result.index(_MENTION_SUFFIX) + len(_MENTION_SUFFIX)
        result = result[:start] + result[end:]
    return result.strip()


class SupportBot(TeamsActivityHandler):
    """Teams activity handler for blocker search and documentation flow.

    Dependencies are injected at construction time so the bot module
    has no import-time dependency on the FastAPI app module.

    Args:
        openai_client: OpenAI client for embedding queries.
        faiss_index: Loaded FAISS index for vector similarity search.
        index_map: Maps FAISS integer IDs to GitHub file paths.
        analytics_table: Azure Table client for conversation state and logging.
        search_fn: Optional override for search (injectable for testing).
        commit_fn: Optional override for GitHub commit (injectable for testing).
        update_index_fn: Optional override for FAISS index update.
        generate_fn: Optional override for document generation.
    """

    def __init__(
        self,
        openai_client: OpenAI | None = None,
        faiss_index: faiss.Index | None = None,
        index_map: dict[str, str] | None = None,
        analytics_table: TableClient | None = None,
        search_fn: Callable[..., list[dict[str, str | float]]] | None = None,
        commit_fn: Callable[..., str] | None = None,
        update_index_fn: Callable[..., None] | None = None,
        generate_fn: Callable[..., str] | None = None,
    ) -> None:
        super().__init__()
        self._openai_client = openai_client
        self._faiss_index = faiss_index
        self._index_map = index_map or {}
        self._analytics_table = analytics_table
        self._search_fn = search_fn
        self._commit_fn = commit_fn
        self._update_index_fn = update_index_fn
        self._generate_fn = generate_fn

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        raw_text: str = turn_context.activity.text or ""
        if not raw_text:
            return

        text = _strip_mention(raw_text)
        if not text:
            return

        user_id: str = turn_context.activity.from_property.id
        conversation_id: str = turn_context.activity.conversation.id

        from blocker_doc_and_solution_bot.conversation_state.session_store import (
            get_session,
        )

        # --- Mode 1: Check for active doc flow session ---
        session: DocFlowState | None = None
        if self._analytics_table is not None:
            session = get_session(user_id, conversation_id, table_client=self._analytics_table)

        if session and session.get("step", "") in (
            "awaiting_error", "awaiting_solution", "awaiting_project",
        ):
            reply = advance_doc_flow(session, text, generate_fn=self._generate_fn)
            if reply:
                await turn_context.send_activity(reply)

            if self._analytics_table is not None:
                create_or_update_session(
                    user_id=user_id,
                    thread_id=conversation_id,
                    state=session,
                    table_client=self._analytics_table,
                )
            return

        # --- Mode 1b: Awaiting approval ---
        if session and session.get("step") == "awaiting_approval":
            lower = text.lower().strip()
            if lower in ("approve", "yes", "ok"):
                slug = _make_slug(session.get("error", "issue"))
                reply = handle_approval(
                    session,
                    approved=True,
                    commit_fn=self._commit_fn,
                    update_index_fn=self._update_index_fn,
                    project=session.get("project", ""),
                    title_slug=slug,
                )
                await turn_context.send_activity(reply)
                if self._analytics_table is not None:
                    from blocker_doc_and_solution_bot.conversation_state.session_store import (
                        delete_session,
                    )
                    delete_session(user_id, conversation_id, table_client=self._analytics_table)
            elif lower in ("decline", "no", "cancel"):
                reply = handle_approval(session, approved=False)
                await turn_context.send_activity(reply)
                if self._analytics_table is not None:
                    from blocker_doc_and_solution_bot.conversation_state.session_store import (
                        delete_session,
                    )
                    delete_session(user_id, conversation_id, table_client=self._analytics_table)
            return

        # --- Mode 2: No-match session + resolution signal → start doc flow ---
        if session and session.get("step") == "no_match" and is_resolution_signal(text):
            reply = "Looks like you found a fix! Let's document it.\n\n" + start_doc_flow(session)
            await turn_context.send_activity(reply)
            if self._analytics_table is not None:
                create_or_update_session(
                    user_id=user_id,
                    thread_id=conversation_id,
                    state=session,
                    table_client=self._analytics_table,
                )
            return

        # --- Mode 3: Normal search flow ---
        if self._search_fn is not None:
            raw = self._search_fn(text)
        else:
            from blocker_doc_and_solution_bot.search_api.search import (
                embed_query,
                search_and_resolve,
            )

            if self._openai_client is None or self._faiss_index is None:
                await turn_context.send_activity("Search index not loaded. Try again later.")
                return

            query_vec = embed_query(text, self._openai_client)
            raw = search_and_resolve(query_vec, self._faiss_index, self._index_map, top_k=3)

        reply = _format_reply(raw)
        await turn_context.send_activity(reply)

        # For no-match, store session for future resolution detection
        best = raw[0] if raw else {"tier": "no_match"}
        if best["tier"] == "no_match":
            no_match_state: DocFlowState = {"last_query": text, "step": "no_match"}
            if self._analytics_table is not None:
                create_or_update_session(
                    user_id=user_id,
                    thread_id=conversation_id,
                    state=no_match_state,
                    table_client=self._analytics_table,
                )


def _make_slug(error_text: str) -> str:
    """Derive a URL-safe title slug from error text."""
    slug = error_text.lower()[:50]
    slug = "".join(c if c.isalnum() else "-" for c in slug)
    slug = slug.strip("-")
    return slug[:50]


def create_adapter() -> BotFrameworkAdapter:
    """Create and return a Bot Framework adapter from environment variables.

    Authentication mode is determined by environment variables:

    - MICROSOFT_APP_ID + MICROSOFT_APP_PASSWORD → password-based auth
    - MICROSOFT_APP_ID only (no password) → user-assigned managed identity auth
    - Neither set → anonymous auth (Bot Framework Emulator)

    For managed identity, the adapter uses ManagedIdentityAppCredentials
    which fetches tokens from the Azure Instance Metadata Service (IMDS).
    The Azure Function must have a user-assigned managed identity assigned
    and that identity must be granted access to the Azure Bot resource.
    """
    app_id = os.getenv("MICROSOFT_APP_ID", "")
    app_password = os.getenv("MICROSOFT_APP_PASSWORD", "")

    if app_id and not app_password:
        # Managed identity: no client secret, use IMDS for tokens
        from botframework.connector.auth import ManagedIdentityAppCredentials

        settings = BotFrameworkAdapterSettings(
            app_id=app_id,
            app_credentials=ManagedIdentityAppCredentials(app_id),
        )
    else:
        settings = BotFrameworkAdapterSettings(app_id, app_password)

    return BotFrameworkAdapter(settings)
