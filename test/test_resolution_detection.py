"""Tests for resolution detection and multi-turn documentation flow."""

from __future__ import annotations

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Resolution signal detection
# ---------------------------------------------------------------------------


def test_detect_resolution_matches_fixed_it() -> None:
    """'fixed it' should be detected as a resolution signal."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("I fixed it!") is True


def test_detect_resolution_matches_sorted() -> None:
    """'sorted' with context should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("sorted now") is True


def test_detect_resolution_matches_turns_out() -> None:
    """'turns out it was' should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("turns out it was a config issue") is True


def test_detect_resolution_matches_resolved() -> None:
    """'resolved' should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("resolved the issue") is True


def test_detect_resolution_matches_works_now() -> None:
    """'works now' should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("it works now!") is True


def test_detect_resolution_matches_solved() -> None:
    """'solved' should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("solved it") is True


def test_detect_resolution_matches_figured_out() -> None:
    """'figured it out' should be detected."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("figured it out finally") is True


def test_detect_resolution_case_insensitive() -> None:
    """Resolution detection should be case-insensitive."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("FIXED IT") is True
    assert is_resolution_signal("SoRtEd") is True


def test_detect_resolution_rejects_noise() -> None:
    """Random messages should not be detected as resolution signals."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import is_resolution_signal

    assert is_resolution_signal("any update on this?") is False
    assert is_resolution_signal("hello") is False
    assert is_resolution_signal("still broken") is False
    assert is_resolution_signal("") is False


# ---------------------------------------------------------------------------
# Doc flow state machine
# ---------------------------------------------------------------------------


def test_doc_flow_starts_with_awaiting_error() -> None:
    """Starting the doc flow should set state to awaiting_error and ask first question."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        start_doc_flow,
    )

    session: DocFlowState = {}
    reply = start_doc_flow(session)
    assert session["step"] == "awaiting_error"
    assert "error" in reply.lower()


def test_doc_flow_collects_error_and_asks_solution() -> None:
    """After providing error, flow should ask for solution."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        advance_doc_flow,
    )

    session: DocFlowState = {"step": "awaiting_error"}
    reply = advance_doc_flow(session, "blob trigger not firing")
    assert session["step"] == "awaiting_solution"
    assert session["error"] == "blob trigger not firing"
    assert "solution" in reply.lower()


def test_doc_flow_collects_solution_and_asks_project() -> None:
    """After providing solution, flow should ask for project."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        advance_doc_flow,
    )

    session: DocFlowState = {
        "step": "awaiting_solution",
        "error": "blob trigger not firing",
    }
    reply = advance_doc_flow(session, "updated the function.json")
    assert session["step"] == "awaiting_project"
    assert session["solution"] == "updated the function.json"
    assert "project" in reply.lower()


def test_doc_flow_collects_project_and_generates_preview() -> None:
    """After providing project, flow should generate doc and ask for approval."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        advance_doc_flow,
    )

    mock_generate = MagicMock(return_value="# Blob Trigger Fix\n\n## Problem\n...")

    session: DocFlowState = {
        "step": "awaiting_project",
        "error": "blob trigger not firing",
        "solution": "updated the function.json",
    }
    reply = advance_doc_flow(
        session,
        "my-function-app",
        generate_fn=mock_generate,
    )
    assert session["step"] == "awaiting_approval"
    assert session["project"] == "my-function-app"
    assert "# Blob Trigger Fix" in reply
    assert "approve" in reply.lower()
    expected_answers = {
        "error": "blob trigger not firing",
        "solution": "updated the function.json",
        "project": "my-function-app",
    }
    mock_generate.assert_called_once_with(expected_answers)


def test_doc_flow_approve_triggers_commit_and_cleanup() -> None:
    """Approving should commit, update index, and clear session."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        handle_approval,
    )

    mock_commit = MagicMock(return_value="https://github.com/url")
    mock_update_index = MagicMock()

    session: DocFlowState = {
        "step": "awaiting_approval",
        "error": "blob trigger not firing",
        "solution": "updated the function.json",
        "project": "my-function-app",
        "markdown": "# Blob Trigger Fix\n\n## Problem\n...",
    }
    result = handle_approval(
        session,
        approved=True,
        commit_fn=mock_commit,
        update_index_fn=mock_update_index,
        project="my-function-app",
        title_slug="blob-trigger-fix",
    )

    assert mock_commit.called
    assert mock_update_index.called
    assert "committed" in result.lower() or "saved" in result.lower()


def test_doc_flow_decline_clears_session() -> None:
    """Declining should clear session without committing."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        handle_approval,
    )

    session: DocFlowState = {
        "step": "awaiting_approval",
        "error": "blob trigger not firing",
        "solution": "updated",
        "project": "p",
        "markdown": "# md",
    }
    result = handle_approval(session, approved=False)
    assert "discarded" in result.lower()
    assert session == {}


def test_doc_flow_advance_ignores_unexpected_step() -> None:
    """If session step is unknown, advance should not change it."""
    from blocker_doc_and_solution_bot.telegram_bot.resolution import (
        DocFlowState,
        advance_doc_flow,
    )

    session: DocFlowState = {"step": "weird_state"}
    reply = advance_doc_flow(session, "some text")
    assert session["step"] == "weird_state"
    assert reply == ""


# ---------------------------------------------------------------------------
# Integration: resolution triggers flow in handle_telegram_update
# ---------------------------------------------------------------------------


def test_handle_update_with_resolution_in_no_match_session_starts_doc_flow() -> None:
    """If a user previously got no-match and now sends a resolution, start doc flow."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_get_session = MagicMock(return_value={
        "last_query": "some query",
        "step": "no_match",
    })
    mock_create_session = MagicMock()
    mock_send = MagicMock()

    update = {
        "update_id": 5,
        "message": {
            "message_id": 100,
            "from": {"id": 999, "first_name": "Test"},
            "chat": {"id": 42, "type": "private"},
            "date": 1700000000,
            "text": "fixed it!",
        },
    }

    handle_telegram_update(
        update,
        bot_token="fake-token",
        send_fn=mock_send,
        get_session_fn=mock_get_session,
        create_session_fn=mock_create_session,
    )

    mock_send.assert_called_once()
    text = mock_send.call_args.kwargs["text"]
    assert "error" in text.lower()


def test_handle_update_continues_doc_flow_mid_conversation() -> None:
    """If in middle of doc flow, next message should advance the state."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_get_session = MagicMock(return_value={
        "step": "awaiting_error",
    })
    mock_create_session = MagicMock()
    mock_send = MagicMock()

    update = {
        "update_id": 6,
        "message": {
            "message_id": 101,
            "from": {"id": 999, "first_name": "Test"},
            "chat": {"id": 42, "type": "private"},
            "date": 1700000000,
            "text": "blob trigger not firing",
        },
    }

    handle_telegram_update(
        update,
        bot_token="fake-token",
        send_fn=mock_send,
        get_session_fn=mock_get_session,
        create_session_fn=mock_create_session,
    )

    mock_send.assert_called_once()
    text = mock_send.call_args.kwargs["text"]
    assert "solution" in text.lower()
    mock_create_session.assert_called_once()


def test_handle_update_with_approve_in_approval_state_commits() -> None:
    """'approve' during awaiting_approval should trigger commit."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_get_session = MagicMock(return_value={
        "step": "awaiting_approval",
        "error": "blob trigger",
        "solution": "updated config",
        "project": "func-app",
        "markdown": "# Fix\n\n## Problem\n...",
    })
    mock_send = MagicMock()
    mock_commit = MagicMock(return_value="https://github.com/url")
    mock_update_index = MagicMock()
    mock_delete_session = MagicMock()

    update = {
        "update_id": 7,
        "message": {
            "message_id": 102,
            "from": {"id": 999, "first_name": "Test"},
            "chat": {"id": 42, "type": "private"},
            "date": 1700000000,
            "text": "approve",
        },
    }

    handle_telegram_update(
        update,
        bot_token="fake-token",
        send_fn=mock_send,
        get_session_fn=mock_get_session,
        commit_fn=mock_commit,
        update_index_fn=mock_update_index,
        delete_session_fn=mock_delete_session,
    )

    mock_commit.assert_called_once()
    mock_update_index.assert_called_once()
    mock_delete_session.assert_called_once()


def test_handle_update_with_decline_in_approval_state_clears() -> None:
    """'decline' during awaiting_approval should clear session."""
    from blocker_doc_and_solution_bot.telegram_bot.bot import handle_telegram_update

    mock_get_session = MagicMock(return_value={
        "step": "awaiting_approval",
        "error": "blah",
        "solution": "blah",
        "project": "p",
        "markdown": "# md",
    })
    mock_send = MagicMock()
    mock_delete_session = MagicMock()

    update = {
        "update_id": 8,
        "message": {
            "message_id": 103,
            "from": {"id": 999, "first_name": "Test"},
            "chat": {"id": 42, "type": "private"},
            "date": 1700000000,
            "text": "decline",
        },
    }

    handle_telegram_update(
        update,
        bot_token="fake-token",
        send_fn=mock_send,
        get_session_fn=mock_get_session,
        delete_session_fn=mock_delete_session,
    )

    mock_delete_session.assert_called_once()
    text = mock_send.call_args.kwargs["text"]
    assert "discarded" in text.lower()
