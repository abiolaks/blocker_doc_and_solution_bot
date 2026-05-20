"""Azure Table Storage-backed conversation state management."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient

_SESSION_TTL = timedelta(hours=24)

# Keys stripped from the entity dict on retrieval (Table Storage metadata)
_STRIP_KEYS = frozenset(
    {"PartitionKey", "RowKey", "Timestamp", "etag", "odata.etag", "odata.metadata"}
)


def get_session(
    user_id: str, thread_id: str, *, table_client: TableClient
) -> dict[str, str] | None:
    """Retrieve session state for a user+thread combination.

    Returns None if the entity doesn't exist or has expired (>24h since updated_at).
    Partition key = user_id, row key = thread_id.
    """
    try:
        entity = dict(table_client.get_entity(partition_key=user_id, row_key=thread_id))
    except ResourceNotFoundError:
        return None

    updated_at_str = entity.get("updated_at", "")
    if not updated_at_str:
        return None
    try:
        updated_at = datetime.fromisoformat(updated_at_str)
    except ValueError:
        return None

    if datetime.now(timezone.utc) - updated_at > _SESSION_TTL:
        return None

    # Strip Table Storage metadata keys before returning
    return {k: v for k, v in entity.items() if k not in _STRIP_KEYS}


def create_or_update_session(
    user_id: str, thread_id: str, state: dict[str, str], *, table_client: TableClient
) -> None:
    """Create or update session state for a user+thread combination.

    Partition key = user_id, row key = thread_id.
    Automatically sets created_at and updated_at ISO 8601 timestamps.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Preserve existing created_at if updating an existing session
    created_at = now
    try:
        existing = dict(table_client.get_entity(partition_key=user_id, row_key=thread_id))
        created_at = existing.get("created_at", now)
    except ResourceNotFoundError:
        pass

    entity = {
        "PartitionKey": user_id,
        "RowKey": thread_id,
        "created_at": created_at,
        "updated_at": now,
        **state,
    }
    table_client.upsert_entity(entity=entity)


def delete_session(
    user_id: str, thread_id: str, *, table_client: TableClient
) -> None:
    """Delete session state for a user+thread combination."""
    table_client.delete_entity(partition_key=user_id, row_key=thread_id)
