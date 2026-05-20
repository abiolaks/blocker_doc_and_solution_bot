"""Tests for conversation state management backed by Azure Table Storage."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient

# ---------------------------------------------------------------------------
# Vertical slice 1: get_session returns None when entity not found
# ---------------------------------------------------------------------------


def test_get_session_returns_none_when_no_entity_exists() -> None:
    """get_session should return None when no entity is found in Table Storage."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import get_session

    mock_table = MagicMock(spec=TableClient)
    mock_table.get_entity.side_effect = ResourceNotFoundError

    result = get_session("user-1", "thread-abc", table_client=mock_table)

    assert result is None
    mock_table.get_entity.assert_called_once_with(
        partition_key="user-1", row_key="thread-abc"
    )


# ---------------------------------------------------------------------------
# Vertical slice 2: get_session returns session dict when entity exists
# ---------------------------------------------------------------------------


def test_get_session_returns_entity_data() -> None:
    """get_session should return the entity dict when found."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import get_session

    mock_table = MagicMock(spec=TableClient)
    entity_data = {
        "PartitionKey": "user-1",
        "RowKey": "thread-abc",
        "step": "awaiting_error",
        "answers": "{}",
        "author": "user-1",
        "created_at": "2026-05-20T10:00:00+00:00",
        "updated_at": "2026-05-20T10:00:00+00:00",
    }
    mock_table.get_entity.return_value = entity_data

    result = get_session("user-1", "thread-abc", table_client=mock_table)

    assert result is not None
    assert result["step"] == "awaiting_error"
    assert result["author"] == "user-1"
    # Should strip storage keys
    assert "PartitionKey" not in result
    assert "RowKey" not in result


# ---------------------------------------------------------------------------
# Vertical slice 3: create_or_update_session
# ---------------------------------------------------------------------------


def test_create_or_update_session_upserts_entity() -> None:
    """create_or_update_session should call upsert_entity with correct partition/row keys."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        create_or_update_session,
    )

    mock_table = MagicMock(spec=TableClient)
    state = {
        "step": "awaiting_solution",
        "answers": '{"error": "ModuleNotFoundError"}',
        "author": "user-2",
    }

    create_or_update_session("user-2", "thread-xyz", state, table_client=mock_table)

    mock_table.upsert_entity.assert_called_once()
    entity = mock_table.upsert_entity.call_args.kwargs["entity"]
    assert entity["PartitionKey"] == "user-2"
    assert entity["RowKey"] == "thread-xyz"
    assert entity["step"] == "awaiting_solution"


# ---------------------------------------------------------------------------
# Vertical slice 4: create then retrieve round-trip
# ---------------------------------------------------------------------------


def test_create_and_retrieve_round_trip() -> None:
    """After create_or_update_session, get_session should retrieve the same data."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        create_or_update_session,
        get_session,
    )

    mock_table = MagicMock(spec=TableClient)
    state = {
        "step": "awaiting_project",
        "answers": '{"error": "KeyError", "solution": "Use .get()"}',
        "author": "user-3",
    }

    stored_entity: dict[str, str] = {}

    def capture_entity(*, entity: dict[str, str]) -> None:
        stored_entity.clear()
        stored_entity.update(entity)

    mock_table.upsert_entity.side_effect = capture_entity
    mock_table.get_entity.return_value = stored_entity

    create_or_update_session("user-3", "thread-def", state, table_client=mock_table)
    result = get_session("user-3", "thread-def", table_client=mock_table)

    assert result is not None
    assert result["step"] == "awaiting_project"
    assert result["answers"] == '{"error": "KeyError", "solution": "Use .get()"}'
    assert result["author"] == "user-3"


# ---------------------------------------------------------------------------
# Vertical slice 5: update existing session
# ---------------------------------------------------------------------------


def test_update_session_preserves_and_merges_fields() -> None:
    """Updating a session should set new step and merge answers."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        create_or_update_session,
        get_session,
    )

    mock_table = MagicMock(spec=TableClient)
    stored: dict[str, str] = {}

    def capture_entity(*, entity: dict[str, str]) -> None:
        stored.clear()
        stored.update(entity)

    mock_table.upsert_entity.side_effect = capture_entity
    mock_table.get_entity.return_value = stored

    # Initial creation: get_entity raises not found → fresh created_at
    mock_table.get_entity.side_effect = ResourceNotFoundError
    create_or_update_session(
        "user-4", "thread-ghi",
        {"step": "awaiting_error", "answers": "{}", "author": "user-4"},
        table_client=mock_table,
    )

    # Update: get_entity returns the stored entity → preserves created_at
    mock_table.get_entity.side_effect = None
    mock_table.get_entity.return_value = stored
    create_or_update_session(
        "user-4", "thread-ghi",
        {"step": "awaiting_solution", "answers": '{"error": "Timeout"}'},
        table_client=mock_table,
    )

    result = get_session("user-4", "thread-ghi", table_client=mock_table)
    assert result is not None
    assert result["step"] == "awaiting_solution"
    assert result["answers"] == '{"error": "Timeout"}'


# ---------------------------------------------------------------------------
# Vertical slice 6: delete_session
# ---------------------------------------------------------------------------


def test_delete_session_removes_entity() -> None:
    """delete_session should call delete_entity with correct keys."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        delete_session,
    )

    mock_table = MagicMock(spec=TableClient)

    delete_session("user-5", "thread-jkl", table_client=mock_table)

    mock_table.delete_entity.assert_called_once_with(
        partition_key="user-5", row_key="thread-jkl"
    )


def test_get_session_returns_none_after_delete() -> None:
    """get_session should return None after a session is deleted."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        delete_session,
        get_session,
    )

    mock_table = MagicMock(spec=TableClient)
    mock_table.get_entity.side_effect = ResourceNotFoundError

    delete_session("user-6", "thread-mno", table_client=mock_table)
    result = get_session("user-6", "thread-mno", table_client=mock_table)

    assert result is None


# ---------------------------------------------------------------------------
# Vertical slice 7: session expiry (older than 24 hours)
# ---------------------------------------------------------------------------


def test_session_expired_returns_none() -> None:
    """get_session should return None for sessions older than 24 hours."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        get_session,
    )

    mock_table = MagicMock(spec=TableClient)
    old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    entity_data = {
        "PartitionKey": "user-7",
        "RowKey": "thread-old",
        "step": "awaiting_error",
        "answers": "{}",
        "author": "user-old",
        "created_at": old_time,
        "updated_at": old_time,
    }
    mock_table.get_entity.return_value = entity_data

    result = get_session("user-7", "thread-old", table_client=mock_table)

    assert result is None


def test_session_within_24h_is_valid() -> None:
    """get_session should return data for sessions less than 24 hours old."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        get_session,
    )

    mock_table = MagicMock(spec=TableClient)
    recent_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
    entity_data = {
        "PartitionKey": "user-8",
        "RowKey": "thread-recent",
        "step": "awaiting_error",
        "answers": "{}",
        "author": "user-recent",
        "created_at": recent_time,
        "updated_at": recent_time,
    }
    mock_table.get_entity.return_value = entity_data

    result = get_session("user-8", "thread-recent", table_client=mock_table)

    assert result is not None
    assert result["step"] == "awaiting_error"


# ---------------------------------------------------------------------------
# Vertical slice 8: create_or_update_session sets timestamps
# ---------------------------------------------------------------------------


def test_create_session_sets_created_at_and_updated_at() -> None:
    """create_or_update_session should set created_at and updated_at timestamps."""
    from blocker_doc_and_solution_bot.conversation_state.session_store import (
        create_or_update_session,
    )

    mock_table = MagicMock(spec=TableClient)
    state = {"step": "awaiting_approval", "answers": "{}", "author": "user-9"}

    create_or_update_session("user-9", "thread-pqr", state, table_client=mock_table)

    entity = mock_table.upsert_entity.call_args.kwargs["entity"]
    assert "created_at" in entity
    assert "updated_at" in entity
    # Parse both as datetimes to compare
    created = datetime.fromisoformat(entity["created_at"])
    updated = datetime.fromisoformat(entity["updated_at"])
    assert updated >= created
