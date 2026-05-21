"""GitHub Contents API integration — commit Markdown documents to the knowledge base."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime

import httpx


def commit_document(
    project: str,
    title_slug: str,
    markdown_content: str,
    *,
    owner: str,
    repo: str,
    github_token: str | None = None,
    http_client: httpx.Client | None = None,
) -> str:
    """Commit a Markdown document to the GitHub knowledge base via the Contents API.

    Args:
        project: Project folder name under knowledge-base/.
        title_slug: URL-safe short slug for the filename.
        markdown_content: Full Markdown content of the document.
        owner: GitHub repository owner (user or org).
        repo: GitHub repository name.
        github_token: GitHub personal access token with contents:write scope.
            Reads GITHUB_PAT env var if not provided.
        http_client: Optional httpx.Client for testing. Creates one if None.

    Returns:
        The HTML URL of the committed file on GitHub.

    Raises:
        ValueError: If the file already exists at the target path (422 response).
        PermissionError: If the GitHub token is invalid or expired (401 response).
    """
    if github_token is None:
        github_token = os.environ["GITHUB_PAT"]

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}-{title_slug}.md"
    path = f"knowledge-base/{project}/{filename}"

    content_bytes = markdown_content.encode("utf-8")
    content_b64 = base64.b64encode(content_bytes).decode("ascii")

    body = {
        "message": f"docs: add {title_slug} for {project}",
        "content": content_b64,
        "branch": "main",
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
    }

    client = http_client or httpx.Client()
    try:
        if http_client is not None:
            response = client.put(url, content=json.dumps(body), headers=headers)
        else:
            response = client.put(url, content=json.dumps(body), headers=headers)

        if response.status_code == 422:
            raise ValueError(
                f"Document already exists at {path}. "
                "Use a different title_slug or delete the existing file."
            )
        if response.status_code == 401:
            raise PermissionError(
                "GitHub token is invalid or expired. Ensure GITHUB_PAT has contents:write scope."
            )

        response.raise_for_status()
        data = response.json()
        return str(data["content"]["html_url"])
    finally:
        if http_client is None:
            client.close()
