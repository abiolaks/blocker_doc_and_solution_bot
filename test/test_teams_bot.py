"""Tests for Microsoft Teams bot — @mention search and doc flow."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botbuilder.core import TurnContext
from botbuilder.schema import Activity, ActivityTypes, ChannelAccount, ConversationAccount
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: _strip_mention
# ---------------------------------------------------------------------------


def test_strip_mention_removes_single_tag() -> None:
    from blocker_doc_and_solution_bot.teams_bot.bot import _strip_mention

    result = _strip_mention("<at>Support Bot</at> blob trigger not firing")
    assert result == "blob trigger not firing"


def test_strip_mention_removes_multiple_tags() -> None:
    from blocker_doc_and_solution_bot.teams_bot.bot import _strip_mention

    result = _strip_mention("<at>Bot</at> <at>User</at> check the pipeline")
    assert result == "check the pipeline"


def test_strip_mention_no_tags_returns_unchanged() -> None:
    from blocker_doc_and_solution_bot.teams_bot.bot import _strip_mention

    assert _strip_mention("deployment failed again") == "deployment failed again"


def test_strip_mention_only_tags_returns_empty() -> None:
    from blocker_doc_and_solution_bot.teams_bot.bot import _strip_mention

    assert _strip_mention("<at>Bot</at>") == ""


def test_strip_mention_whitespace_around_tags() -> None:
    from blocker_doc_and_solution_bot.teams_bot.bot import _strip_mention

    assert _strip_mention("  <at>Bot</at>  hello  ") == "hello"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_turn_context(text: str, user_id: str = "user-1", conv_id: str = "conv-1") -> MagicMock:
    """Build a mock TurnContext with a message activity.

    send_activity is an AsyncMock so the bot can call await on it.
    """
    ctx = MagicMock(spec=TurnContext)
    ctx.activity = Activity(
        type=ActivityTypes.message,
        text=text,
        from_property=ChannelAccount(id=user_id),
        conversation=ConversationAccount(id=conv_id),
    )
    ctx.send_activity = AsyncMock()
    return ctx


# ---------------------------------------------------------------------------
# Unit tests: SupportBot.on_message_activity — search modes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bot_match_tier_reply() -> None:
    """A message with a match result should reply with match-tier wording."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    mock_search = MagicMock(return_value=[
        {"score": 0.92, "path": "kb/proj/fix.md", "tier": "match"},
    ])
    bot = SupportBot(search_fn=mock_search)
    ctx = _make_turn_context("<at>Support Bot</at> blob trigger not firing")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "Found a match" in reply
    assert "fix.md" in reply


@pytest.mark.asyncio
async def test_bot_related_tier_reply() -> None:
    """Related tier should use 'might help' wording."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    mock_search = MagicMock(return_value=[
        {"score": 0.65, "path": "kb/proj/similar.md", "tier": "related"},
    ])
    bot = SupportBot(search_fn=mock_search)
    ctx = _make_turn_context("<at>Bot</at> deployment timeout")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "something related" in reply.lower()
    assert "not an exact match" in reply.lower()
    assert "similar.md" in reply


@pytest.mark.asyncio
async def test_bot_no_match_reply() -> None:
    """No-match tier should use 'watch this thread' wording."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    mock_search = MagicMock(return_value=[
        {"score": 0.3, "path": "", "tier": "no_match"},
    ])
    bot = SupportBot(search_fn=mock_search)
    ctx = _make_turn_context("<at>Bot</at> completely novel error")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "nothing in the knowledge base" in reply.lower()
    assert "watch this" in reply.lower()


@pytest.mark.asyncio
async def test_bot_empty_text_ignored() -> None:
    """A message with no text should not call search or send."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    mock_search = MagicMock()
    bot = SupportBot(search_fn=mock_search)
    ctx = _make_turn_context("")

    await bot.on_message_activity(ctx)

    mock_search.assert_not_called()
    ctx.send_activity.assert_not_awaited()


@pytest.mark.asyncio
async def test_bot_mention_only_ignored() -> None:
    """A message that is only an @mention tag should be ignored."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    mock_search = MagicMock()
    bot = SupportBot(search_fn=mock_search)
    ctx = _make_turn_context("<at>Support Bot</at>")

    await bot.on_message_activity(ctx)

    mock_search.assert_not_called()
    ctx.send_activity.assert_not_awaited()


# ---------------------------------------------------------------------------
# Unit tests: SupportBot.on_message_activity — doc flow modes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bot_active_doc_flow_session() -> None:
    """When session is in doc flow, bot should advance the state machine."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    now = datetime.now(timezone.utc).isoformat()
    table_mock = MagicMock()
    # Simulate get_session returning an active doc flow session
    # Entity stored by create_or_update_session: state keys are flattened + metadata
    # return_value used so both get_session and create_or_update_session can call get_entity
    table_mock.get_entity.return_value = {
        "step": "awaiting_error",
        "PartitionKey": "user-1",
        "RowKey": "conv-1",
        "created_at": now,
        "updated_at": now,
    }

    bot = SupportBot(analytics_table=table_mock)
    ctx = _make_turn_context("<at>Bot</at> ModuleNotFoundError: sklearn")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "solution" in reply.lower()  # asking for solution next


@pytest.mark.asyncio
async def test_bot_approval_approve() -> None:
    """When session is awaiting_approval and user says 'approve', commit should happen."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    now = datetime.now(timezone.utc).isoformat()
    table_mock = MagicMock()
    table_mock.get_entity.return_value = {
        "step": "awaiting_approval", "error": "blah", "markdown": "# Test", "project": "proj",
        "PartitionKey": "user-1", "RowKey": "conv-1", "created_at": now, "updated_at": now,
    }
    mock_commit = MagicMock(return_value="https://github.com/owner/repo/blob/main/kb/proj/doc.md")

    bot = SupportBot(analytics_table=table_mock, commit_fn=mock_commit)
    ctx = _make_turn_context("<at>Bot</at> approve")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "saved" in reply.lower()
    mock_commit.assert_called_once()


@pytest.mark.asyncio
async def test_bot_approval_decline() -> None:
    """When session is awaiting_approval and user says 'decline', session is discarded."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    now = datetime.now(timezone.utc).isoformat()
    table_mock = MagicMock()
    table_mock.get_entity.return_value = {
        "step": "awaiting_approval", "error": "blah", "markdown": "# Test",
        "PartitionKey": "user-1", "RowKey": "conv-1", "created_at": now, "updated_at": now,
    }
    mock_commit = MagicMock()

    bot = SupportBot(analytics_table=table_mock, commit_fn=mock_commit)
    ctx = _make_turn_context("<at>Bot</at> decline")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "discarded" in reply.lower()
    mock_commit.assert_not_called()


# ---------------------------------------------------------------------------
# Unit tests: SupportBot.on_message_activity — resolution detection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bot_resolution_signal_starts_doc_flow() -> None:
    """When in no_match session and user says 'fixed it', bot should start doc flow."""
    from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot

    now = datetime.now(timezone.utc).isoformat()
    table_mock = MagicMock()
    table_mock.get_entity.return_value = {
        "last_query": "old error", "step": "no_match",
        "PartitionKey": "user-1", "RowKey": "conv-1", "created_at": now, "updated_at": now,
    }

    bot = SupportBot(analytics_table=table_mock)
    ctx = _make_turn_context("<at>Bot</at> fixed it by restarting the function app")

    await bot.on_message_activity(ctx)

    ctx.send_activity.assert_awaited_once()
    reply = ctx.send_activity.call_args[0][0]
    assert "fix" in reply.lower()
    assert "document" in reply.lower()


# ---------------------------------------------------------------------------
# Integration test: /messages endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_messages_endpoint_returns_200() -> None:
    """POST /messages should return 200 after processing a message activity."""
    from blocker_doc_and_solution_bot.search_api.app import app

    # Mock the adapter's process_activity to simulate a successful message turn.
    async def _mock_process_activity(activity, auth_header, callback):
        return None

    mock_adapter = MagicMock()
    mock_adapter.process_activity = AsyncMock(side_effect=_mock_process_activity)

    with (
        patch(
            "blocker_doc_and_solution_bot.search_api.app.create_adapter",
            return_value=mock_adapter,
        ),
        patch("blocker_doc_and_solution_bot.search_api.app.SupportBot"),
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch("blocker_doc_and_solution_bot.search_api.app._analytics_table", MagicMock()),
    ):
        client = TestClient(app)
        body = {
            "type": "message",
            "text": "<at>Support Bot</at> blob trigger not firing",
            "from": {"id": "user-1"},
            "conversation": {"id": "conv-1"},
        }
        response = client.post("/messages", json=body)
        assert response.status_code == 200


def test_messages_endpoint_invoke_returns_response_body() -> None:
    """POST /messages with an invoke activity should return the adapter's InvokeResponse."""
    from blocker_doc_and_solution_bot.search_api.app import app

    async def _mock_process_activity(activity, auth_header, callback):
        from botbuilder.schema import InvokeResponse
        return InvokeResponse(status=200, body={"ok": True})

    mock_adapter = MagicMock()
    mock_adapter.process_activity = AsyncMock(side_effect=_mock_process_activity)

    with (
        patch(
            "blocker_doc_and_solution_bot.search_api.app.create_adapter",
            return_value=mock_adapter,
        ),
        patch("blocker_doc_and_solution_bot.search_api.app.SupportBot"),
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch("blocker_doc_and_solution_bot.search_api.app._analytics_table", MagicMock()),
    ):
        client = TestClient(app)
        body = {
            "type": "invoke",
            "name": "composeExtension/query",
            "from": {"id": "user-1"},
            "conversation": {"id": "conv-1"},
        }
        response = client.post("/messages", json=body)
        assert response.status_code == 200
        assert response.json() == {"ok": True}


# ---------------------------------------------------------------------------
# Unit tests: create_adapter
# ---------------------------------------------------------------------------


def test_create_adapter_with_app_id_and_password() -> None:
    """create_adapter should use MICROSOFT_APP_ID and MICROSOFT_APP_PASSWORD when set."""
    from blocker_doc_and_solution_bot.teams_bot.bot import create_adapter

    with patch.dict(
        "os.environ",
        {"MICROSOFT_APP_ID": "app-id", "MICROSOFT_APP_PASSWORD": "secret"},
    ):
        adapter = create_adapter()
        assert adapter is not None


def test_create_adapter_with_managed_identity() -> None:
    """Use ManagedIdentityAppCredentials when app_id set but no password."""
    from blocker_doc_and_solution_bot.teams_bot.bot import create_adapter

    with (
        patch.dict("os.environ", {"MICROSOFT_APP_ID": "app-id"}, clear=True),
        patch(
            "botframework.connector.auth.ManagedIdentityAppCredentials"
        ) as mock_creds,
    ):
        adapter = create_adapter()
        assert adapter is not None
        mock_creds.assert_called_once_with("app-id")


def test_create_adapter_without_credentials() -> None:
    """create_adapter should work with empty strings (anonymous for emulator)."""
    from blocker_doc_and_solution_bot.teams_bot.bot import create_adapter

    with patch.dict("os.environ", {}, clear=True):
        adapter = create_adapter()
        assert adapter is not None
