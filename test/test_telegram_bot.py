"""Tests for Telegram bot webhook — search & reply integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: handle_telegram_update
# ---------------------------------------------------------------------------


def _make_message_update(text: str, chat_id: int = 123, message_id: int = 456) -> dict[str, object]:
    """Build a minimal Telegram message update dict."""
    return {
        "update_id": 1,
        "message": {
            "message_id": message_id,
            "from": {"id": 999, "is_bot": False, "first_name": "Test"},
            "chat": {"id": chat_id, "type": "private"},
            "date": 1700000000,
            "text": text,
        },
    }


def test_handle_update_searches_and_sends_match_reply() -> None:
    """A message update should search and reply with match-tier wording."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock(return_value=[
        {"score": 0.92, "path": "kb/proj/fix.md", "tier": "match"},
    ])

    mock_send = MagicMock()

    update = _make_message_update("blob trigger not firing")
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
    )

    mock_search.assert_called_once_with("blob trigger not firing")
    mock_send.assert_called_once()
    call_args = mock_send.call_args
    assert call_args.kwargs["chat_id"] == 123
    assert "Found a match" in call_args.kwargs["text"]
    assert "fix.md" in call_args.kwargs["text"]
    assert call_args.kwargs["reply_to_message_id"] == 456


def test_handle_update_sends_related_tier_reply() -> None:
    """Related tier should use 'might help' wording."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock(return_value=[
        {"score": 0.65, "path": "kb/proj/similar.md", "tier": "related"},
    ])
    mock_send = MagicMock()

    update = _make_message_update("deployment timeout")
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
    )

    mock_send.assert_called_once()
    text = mock_send.call_args.kwargs["text"]
    assert "something related" in text.lower()
    assert "not an exact match" in text.lower()
    assert "similar.md" in text


def test_handle_update_sends_no_match_reply() -> None:
    """No-match tier should use 'I'll watch this thread' wording."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock(return_value=[
        {"score": 0.3, "path": "", "tier": "no_match"},
    ])
    mock_send = MagicMock()

    update = _make_message_update("completely novel error")
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
    )

    mock_send.assert_called_once()
    text = mock_send.call_args.kwargs["text"]
    assert "nothing in the knowledge base" in text.lower()
    assert "watch this" in text.lower()


def test_handle_update_with_no_text_is_ignored() -> None:
    """Updates without message text (e.g., stickers) should not call search."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock()
    mock_send = MagicMock()

    update = {"update_id": 2, "message": {"chat": {"id": 123}, "sticker": {}}}
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
    )

    mock_search.assert_not_called()
    mock_send.assert_not_called()


def test_handle_update_no_match_stores_session() -> None:
    """No-match results should store the chat in conversation state."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock(return_value=[
        {"score": 0.2, "path": "", "tier": "no_match"},
    ])
    mock_send = MagicMock()
    mock_store_session = MagicMock()

    update = _make_message_update("new blocker", chat_id=42, message_id=10)
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
        store_session_fn=mock_store_session,
    )

    mock_store_session.assert_called_once_with(chat_id=42, message_id=10)


def test_handle_update_match_does_not_store_session() -> None:
    """Match results should NOT store session state."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_search = MagicMock(return_value=[
        {"score": 0.95, "path": "kb/fix.md", "tier": "match"},
    ])
    mock_send = MagicMock()
    mock_store_session = MagicMock()

    update = _make_message_update("known error")
    handle_telegram_update(
        update,
        bot_token="fake-token",
        search_fn=mock_search,
        send_fn=mock_send,
        store_session_fn=mock_store_session,
    )

    mock_store_session.assert_not_called()


def test_send_telegram_message_calls_bot_api() -> None:
    """send_telegram_message should POST to the Telegram Bot API."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import send_telegram_message

    mock_httpx = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx.post.return_value = mock_response

    send_telegram_message(
        chat_id=123,
        text="hello",
        bot_token="tok",
        http_client=mock_httpx,
    )

    mock_httpx.post.assert_called_once()
    url = mock_httpx.post.call_args[0][0]
    assert "api.telegram.org/bottok/sendMessage" in url
    body = mock_httpx.post.call_args.kwargs["json"]
    assert body["chat_id"] == 123
    assert body["text"] == "hello"


def test_send_telegram_message_includes_reply_to() -> None:
    """When reply_to_message_id is provided, it should be in the payload."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import send_telegram_message

    mock_httpx = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx.post.return_value = mock_response

    send_telegram_message(
        chat_id=123,
        text="reply",
        bot_token="tok",
        reply_to_message_id=789,
        http_client=mock_httpx,
    )

    body = mock_httpx.post.call_args.kwargs["json"]
    assert body["reply_to_message_id"] == 789


# ---------------------------------------------------------------------------
# Integration test: /telegram/webhook endpoint
# ---------------------------------------------------------------------------


def test_webhook_endpoint_returns_200() -> None:
    """POST /telegram/webhook should return 200 OK."""
    from blocker_doc_and_solution_bot.search_api.app import app

    # Need to mock module-level state + search + telegram send
    with (
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
        patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "test-token"}),
        patch(
            "blocker_doc_and_solution_bot.telegram_bot.bot.send_telegram_message"
        ) as mock_send,
        patch(
            "blocker_doc_and_solution_bot.telegram_bot.bot.search_and_resolve",
            return_value=[{"score": 0.92, "path": "kb/fix.md", "tier": "match"}],
        ),
    ):
        client = TestClient(app)
        update = _make_message_update("blob trigger")
        response = client.post("/telegram/webhook", json=update)
        assert response.status_code == 200
        mock_send.assert_called_once()


def test_webhook_endpoint_without_token_returns_503() -> None:
    """When TELEGRAM_BOT_TOKEN is not set, the endpoint should 503."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with (
        patch("blocker_doc_and_solution_bot.search_api.app._openai_client", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._faiss_index", MagicMock()),
        patch("blocker_doc_and_solution_bot.search_api.app._index_map", {}),
    ):
        client = TestClient(app)
        update = _make_message_update("test")
        response = client.post("/telegram/webhook", json=update)
        assert response.status_code == 503
