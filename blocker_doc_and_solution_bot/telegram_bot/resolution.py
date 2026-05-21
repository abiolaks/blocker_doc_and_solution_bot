"""Resolution detection and multi-turn documentation flow state machine."""

from __future__ import annotations

from collections.abc import Callable

# Phrases that indicate a blocker was resolved
_RESOLUTION_PATTERNS = [
    "fixed it",
    "sorted",
    "turns out",
    "resolved",
    "works now",
    "solved",
    "figured it out",
]

DocFlowState = dict[str, str]


def is_resolution_signal(text: str) -> bool:
    """Check if a message text indicates a blocker has been resolved.

    Case-insensitive match against known resolution phrases.
    """
    lower = text.lower()
    return any(pattern in lower for pattern in _RESOLUTION_PATTERNS)


def start_doc_flow(session: DocFlowState) -> str:
    """Begin the documentation flow by asking for the error.

    Sets session step to 'awaiting_error'.
    Returns the question text to send to the user.
    """
    session["step"] = "awaiting_error"
    return "What was the error or unexpected behavior?"


def advance_doc_flow(
    session: DocFlowState,
    user_text: str,
    *,
    generate_fn: Callable[..., str] | None = None,
) -> str:
    """Advance the multi-turn documentation flow based on current step.

    Args:
        session: Mutable session dict tracking flow state.
        user_text: The user's reply message text.
        generate_fn: Function to call for doc generation on project step.
            Signature: generate_fn(answers: dict) -> str

    Returns:
        Reply text to send to the user, or empty string if step is unknown.
    """
    step = session.get("step", "")

    if step == "awaiting_error":
        session["error"] = user_text
        session["step"] = "awaiting_solution"
        return "What was the solution? What steps fixed it?"

    if step == "awaiting_solution":
        session["solution"] = user_text
        session["step"] = "awaiting_project"
        return "Which project or service was this related to?"

    if step == "awaiting_project":
        session["project"] = user_text
        answers = {
            "error": session["error"],
            "solution": session["solution"],
            "project": session["project"],
        }

        if generate_fn is not None:
            markdown = generate_fn(answers)
        else:
            from blocker_doc_and_solution_bot.doc_generator.generator import (
                generate_document,
            )
            markdown = generate_document(answers)

        session["markdown"] = markdown
        session["step"] = "awaiting_approval"
        return (
            f"Here's the generated knowledge base entry:\n\n{markdown}\n\n"
            "Reply 'approve' to save to GitHub or 'decline' to discard."
        )

    return ""


def handle_approval(
    session: DocFlowState,
    approved: bool,
    *,
    commit_fn: Callable[..., str] | None = None,
    update_index_fn: Callable[..., None] | None = None,
    project: str = "",
    title_slug: str = "",
) -> str:
    """Process approval or decline of a generated document.

    On approve: commits to GitHub and updates FAISS index.
    On decline: discards and cleans up.

    Session is cleared in both cases.
    """
    if not approved:
        session.clear()
        return "Discarded. Nothing was saved."

    markdown = session.get("markdown", "")
    session.clear()

    if commit_fn is not None:
        commit_fn(
            project=project,
            title_slug=title_slug,
            markdown_content=markdown,
        )
    else:
        import os

        from blocker_doc_and_solution_bot.github_commit.committer import (
            commit_document,
        )

        owner = os.getenv("GITHUB_REPO_OWNER", "abiolaks")
        repo = os.getenv("GITHUB_REPO_NAME", "blocker_doc_and_solution_bot")
        commit_document(
            project=project,
            title_slug=title_slug,
            markdown_content=markdown,
            owner=owner,
            repo=repo,
        )

    if update_index_fn is not None:
        update_index_fn()
    else:
        import os
        from datetime import datetime

        from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index
        from blocker_doc_and_solution_bot.search_api.app import (
            _blob_client,
            _openai_client,
        )

        if _openai_client is not None and _blob_client is not None:
            filename = f"{datetime.now().strftime('%Y-%m-%d')}-{title_slug}.md"
            path = f"knowledge-base/{project}/{filename}"
            container = os.getenv("AZURE_STORAGE_CONTAINER", "faiss-index")
            add_document_to_index(
                document_content=markdown,
                document_path=path,
                openai_client=_openai_client,
                blob_client=_blob_client,
                container_name=container,
            )

    return "Saved to the knowledge base!"
