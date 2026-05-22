"""Analytics event logging to Azure Table Storage."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from azure.data.tables import TableClient

_PARTITION_KEY = "analytics"


def log_event(
    event_type: str,
    user: str,
    *,
    query: str = "",
    match_tier: str = "",
    result_path: str = "",
    project: str = "",
    doc_path: str = "",
    table_client: TableClient,
) -> None:
    """Log a search or commit event to the analytics Table Storage table.

    Fire-and-forget pattern — does not raise on failure.

    Args:
        event_type: "search" or "commit".
        user: User identifier (Teams ID, Telegram ID, or name).
        query: The search query text (search events only).
        match_tier: "match", "related", or "no_match" (search events only).
        result_path: GitHub file path if matched (search events only).
        project: Project folder name (commit events only).
        doc_path: Committed file path (commit events only).
        table_client: Azure TableClient for the analytics table.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    row_key = f"{timestamp}_{uuid.uuid4().hex[:8]}"

    entity = {
        "PartitionKey": _PARTITION_KEY,
        "RowKey": row_key,
        "timestamp": timestamp,
        "event_type": event_type,
        "user": user,
    }

    if event_type == "search":
        entity["query"] = query
        entity["match_tier"] = match_tier
        entity["result_path"] = result_path
    elif event_type == "commit":
        entity["project"] = project
        entity["doc_path"] = doc_path

    try:
        table_client.upsert_entity(entity=entity)
    except Exception:
        # Silently swallow — analytics must not break the main flow
        pass
