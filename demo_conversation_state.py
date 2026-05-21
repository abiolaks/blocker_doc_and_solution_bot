"""Interactive demo: exercises the conversation state module against live Azure Table Storage.

Reads AZURE_STORAGE_CONNECTION_STRING from .env.
"""

from __future__ import annotations

import os

from azure.data.tables import TableClient, TableServiceClient
from dotenv import load_dotenv

from blocker_doc_and_solution_bot.conversation_state.session_store import (
    create_or_update_session,
    delete_session,
    get_session,
)

TABLE_NAME = "sessionstatedemo"


def main() -> None:
    load_dotenv()

    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

    # 1. Set up the table
    print("=== Setting up Azure Table Storage ===")
    service = TableServiceClient.from_connection_string(conn_str)
    try:
        service.create_table(TABLE_NAME)
        print(f"  Created table '{TABLE_NAME}'")
    except Exception:
        print(f"  Table '{TABLE_NAME}' already exists, reusing it")

    table_client = TableClient.from_connection_string(conn_str, TABLE_NAME)

    # 2. get_session returns None when nothing stored
    print("\n=== Step 1: get_session (nothing stored) ===")
    result = get_session("alice", "thread-001", table_client=table_client)
    print(f"  Result: {result}")
    assert result is None, "Expected None for missing session!"

    # 3. Create a session
    print("\n=== Step 2: create_or_update_session ===")
    state = {"step": "awaiting_error", "answers": "{}", "author": "alice"}
    create_or_update_session("alice", "thread-001", state, table_client=table_client)
    print(f"  Created session for alice/thread-001 with state: {state}")

    # 4. Retrieve it
    print("\n=== Step 3: get_session (after create) ===")
    session = get_session("alice", "thread-001", table_client=table_client)
    print(f"  Retrieved: {session}")
    assert session is not None
    assert session["step"] == "awaiting_error"
    assert session["author"] == "alice"
    assert session.get("created_at") is not None
    assert session.get("updated_at") is not None
    print("  OK: step, author, and timestamps present")

    # 5. Update the session (simulate moving to next question)
    print("\n=== Step 4: update session (next step) ===")
    state2 = {"step": "awaiting_solution", "answers": '{"error": "KeyError on user_id"}'}
    create_or_update_session("alice", "thread-001", state2, table_client=table_client)
    updated = get_session("alice", "thread-001", table_client=table_client)
    print(f"  Updated: {updated}")
    assert updated is not None
    assert updated["step"] == "awaiting_solution"
    assert updated["answers"] == '{"error": "KeyError on user_id"}'
    created_at_first = session["created_at"]
    created_at_after_update = updated["created_at"]
    assert created_at_first == created_at_after_update, "created_at should be preserved across updates!"
    print(f"  OK: created_at preserved ({created_at_first})")

    # 6. Different user, different thread — isolated
    print("\n=== Step 5: separate user/thread isolation ===")
    state_bob = {"step": "awaiting_project", "answers": "{}", "author": "bob"}
    create_or_update_session("bob", "thread-002", state_bob, table_client=table_client)
    bob_session = get_session("bob", "thread-002", table_client=table_client)
    alice_session = get_session("alice", "thread-001", table_client=table_client)
    print(f"  Bob's session:   {bob_session}")
    print(f"  Alice's session: {alice_session}")
    assert bob_session is not None and bob_session["author"] == "bob"
    assert alice_session is not None and alice_session["author"] == "alice"
    print("  OK: sessions are isolated by user_id + thread_id")

    # 7. Delete and verify gone
    print("\n=== Step 6: delete_session ===")
    delete_session("alice", "thread-001", table_client=table_client)
    gone = get_session("alice", "thread-001", table_client=table_client)
    print(f"  After delete: {gone}")
    assert gone is None
    print("  OK: session deleted")

    # Clean up
    try:
        service.delete_table(TABLE_NAME)
        print(f"\n  Cleaned up table '{TABLE_NAME}'")
    except Exception:
        print(f"\n  (kept table '{TABLE_NAME}' for inspection)")

    print("\n=== All checks passed against live Azure Table Storage ===")


if __name__ == "__main__":
    main()
