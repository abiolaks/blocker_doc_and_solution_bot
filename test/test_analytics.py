"""Tests for analytics logging module — search and commit event logging."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: log_event function
# ---------------------------------------------------------------------------


def test_log_search_event_calls_upsert() -> None:
    """log_event for search should upsert an entity with correct fields."""
    from blocker_doc_and_solution_bot.analytics.logger import log_event

    mock_table = MagicMock()
    log_event(
        event_type="search",
        user="user-123",
        query="blob trigger error",
        match_tier="match",
        result_path="kb/proj/fix.md",
        table_client=mock_table,
    )

    mock_table.upsert_entity.assert_called_once()
    entity = mock_table.upsert_entity.call_args.kwargs["entity"]
    assert entity["event_type"] == "search"
    assert entity["user"] == "user-123"
    assert entity["query"] == "blob trigger error"
    assert entity["match_tier"] == "match"
    assert entity["result_path"] == "kb/proj/fix.md"
    assert "timestamp" in entity
    # ISO 8601 format
    datetime.fromisoformat(entity["timestamp"])


def test_log_search_event_no_match() -> None:
    """No-match search should have match_tier 'no_match' and empty result_path."""
    from blocker_doc_and_solution_bot.analytics.logger import log_event

    mock_table = MagicMock()
    log_event(
        event_type="search",
        user="user-456",
        query="unknown error",
        match_tier="no_match",
        result_path="",
        table_client=mock_table,
    )

    entity = mock_table.upsert_entity.call_args.kwargs["entity"]
    assert entity["match_tier"] == "no_match"
    assert entity["result_path"] == ""


def test_log_commit_event_calls_upsert() -> None:
    """log_event for commit should upsert with project and doc_path."""
    from blocker_doc_and_solution_bot.analytics.logger import log_event

    mock_table = MagicMock()
    log_event(
        event_type="commit",
        user="user-789",
        project="my-app",
        doc_path="knowledge-base/my-app/2026-05-21-fix.md",
        table_client=mock_table,
    )

    entity = mock_table.upsert_entity.call_args.kwargs["entity"]
    assert entity["event_type"] == "commit"
    assert entity["user"] == "user-789"
    assert entity["project"] == "my-app"
    assert entity["doc_path"] == "knowledge-base/my-app/2026-05-21-fix.md"
    assert "timestamp" in entity


def test_log_event_generates_unique_row_keys() -> None:
    """Each log event should have a unique RowKey (timestamp-based UUID)."""
    from blocker_doc_and_solution_bot.analytics.logger import log_event

    mock_table = MagicMock()
    log_event(event_type="search", user="u", table_client=mock_table)
    row1 = mock_table.upsert_entity.call_args.kwargs["entity"]["RowKey"]

    log_event(event_type="search", user="u", table_client=mock_table)
    row2 = mock_table.upsert_entity.call_args.kwargs["entity"]["RowKey"]

    assert row1 != row2


# ---------------------------------------------------------------------------
# Integration tests: analytics instrumented in endpoints
# ---------------------------------------------------------------------------


def test_search_endpoint_logs_analytics() -> None:
    """POST /search should log an analytics event."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with (
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch("blocker_doc_and_solution_bot.search_api.app._analytics_table", MagicMock()),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.search_and_resolve",
            return_value=[{"score": 0.92, "path": "kb/fix.md", "tier": "match"}],
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.embed_query",
            return_value=MagicMock(),
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.log_event"
        ) as mock_log,
    ):
        client = TestClient(app)
        response = client.post("/search", json={"query": "blob trigger"})
        assert response.status_code == 200

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["event_type"] == "search"
        assert call_kwargs["query"] == "blob trigger"
        assert call_kwargs["match_tier"] == "match"


def test_save_endpoint_logs_analytics() -> None:
    """POST /save should log a commit analytics event."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with (
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._blob_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch("blocker_doc_and_solution_bot.search_api.app._analytics_table", MagicMock()),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.commit_document",
            return_value="https://github.com/url",
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.add_document_to_index",
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.log_event"
        ) as mock_log,
    ):
        client = TestClient(app)
        response = client.post("/save", json={
            "project": "my-app",
            "title_slug": "fix",
            "markdown": "# Fix\n\n## Problem\n...",
        })
        assert response.status_code == 200

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["event_type"] == "commit"
        assert call_kwargs["project"] == "my-app"


def test_telegram_search_logs_analytics() -> None:
    """Telegram webhook search should log an analytics event via the bot handler."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with (
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch("blocker_doc_and_solution_bot.search_api.app._analytics_table", MagicMock()),
        patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"}),
        patch(
            "blocker_doc_and_solution_bot.telegram_bot.bot.send_telegram_message"
        ),
        patch(
            "blocker_doc_and_solution_bot.telegram_bot.bot.search_and_resolve",
            return_value=[{"score": 0.92, "path": "kb/fix.md", "tier": "match"}],
        ),
        patch(
            "blocker_doc_and_solution_bot.analytics.logger.log_event"
        ) as mock_log,
    ):
        client = TestClient(app)
        update = {
            "update_id": 1,
            "message": {
                "message_id": 42,
                "from": {"id": 999, "first_name": "Test"},
                "chat": {"id": 123, "type": "private"},
                "date": 1700000000,
                "text": "deployment failure",
            },
        }
        response = client.post("/telegram/webhook", json=update)
        assert response.status_code == 200

        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["event_type"] == "search"
        assert call_kwargs["query"] == "deployment failure"
        assert call_kwargs["user"] == "999"


def test_handle_approval_commits_logs_analytics() -> None:
    """When handle_approval is called with approved=True, it should log a commit event."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        handle_approval,
    )

    mock_commit = MagicMock(return_value="https://github.com/url")
    mock_update_index = MagicMock()
    mock_analytics = MagicMock()

    with (
        patch(
            "blocker_doc_and_solution_bot.telegram_bot.resolution.log_event"
        ) as mock_log,
        patch(
            "blocker_doc_and_solution_bot.search_api.app._analytics_table",
            mock_analytics,
        ),
    ):
        session: DocFlowState = {
            "step": "awaiting_approval",
            "error": "deploy fail",
            "solution": "restarted",
            "project": "func-app",
            "markdown": "# Fix\n\n## Problem\n...",
        }
        result = handle_approval(
            session,
            approved=True,
            commit_fn=mock_commit,
            update_index_fn=mock_update_index,
            project="func-app",
            title_slug="deploy-fail",
        )

        assert "Saved" in result
        mock_log.assert_called_once()
        call_kwargs = mock_log.call_args.kwargs
        assert call_kwargs["event_type"] == "commit"
        assert call_kwargs["project"] == "func-app"
        assert call_kwargs["user"] == "telegram"
