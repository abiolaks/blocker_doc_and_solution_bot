"""Tests for GitHub commit integration module and /save endpoint."""

from __future__ import annotations

import base64
import json
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: commit_document function
# ---------------------------------------------------------------------------


def test_commit_document_returns_url(tmp_path: Path) -> None:
    """commit_document should PUT to GitHub Contents API and return the HTML URL."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    today = datetime.now().strftime("%Y-%m-%d")
    expected_path = f"knowledge-base/my-project/{today}-some-error.md"
    expected_url = f"https://github.com/abiolaks/blocker_doc_and_solution_bot/blob/main/{expected_path}"

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "content": {
            "html_url": expected_url,
            "path": expected_path,
        }
    }
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    url = commit_document(
        project="my-project",
        title_slug="some-error",
        markdown_content="# Some Error\n\n## Problem\n...",
        owner="abiolaks",
        repo="blocker_doc_and_solution_bot",
        github_token="fake-token",
        http_client=mock_http,
    )

    assert url == expected_url

    # Verify the PUT call
    mock_http.put.assert_called_once()
    call_args = mock_http.put.call_args

    assert call_args[0][0].endswith(expected_path)

    # Body should contain base64-encoded content
    body = json.loads(call_args.kwargs["content"])
    assert body["branch"] == "main"
    assert body["message"].startswith("docs: add")
    decoded = base64.b64decode(body["content"]).decode("utf-8")
    assert decoded == "# Some Error\n\n## Problem\n..."


def test_commit_document_filename_includes_todays_date(tmp_path: Path) -> None:
    """The filename generated must start with today's date in YYYY-MM-DD format."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "content": {
            "html_url": "https://github.com/abiolaks/blocker_doc_and_solution_bot/blob/main/knowledge-base/p/cool-fix.md",
            "path": "knowledge-base/p/cool-fix.md",
        }
    }
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    commit_document(
        project="p",
        title_slug="cool-fix",
        markdown_content="# fix",
        owner="abiolaks",
        repo="blocker_doc_and_solution_bot",
        github_token="fake-token",
        http_client=mock_http,
    )

    call_args = mock_http.put.call_args
    url_path: str = call_args[0][0]
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"{today}-cool-fix.md" in url_path


def test_commit_document_commit_message_format() -> None:
    """Commit message must follow docs: add <title_slug> for <project> format."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "content": {"html_url": "https://github.com/url", "path": "kb/x/file.md"}
    }
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    commit_document(
        project="my-team-project",
        title_slug="numpy-version-conflict",
        markdown_content="# test",
        owner="abiolaks",
        repo="blocker_doc_and_solution_bot",
        github_token="fake-token",
        http_client=mock_http,
    )

    body = json.loads(mock_http.put.call_args.kwargs["content"])
    assert body["message"] == "docs: add numpy-version-conflict for my-team-project"


def test_commit_document_raises_on_422_file_exists() -> None:
    """If GitHub returns 422, raise ValueError indicating file already exists."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 422
    mock_response.json.return_value = {"message": "Invalid request. 'sha' wasn't supplied."}
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with pytest.raises(ValueError, match="already exists"):
        commit_document(
            project="p",
            title_slug="dup-slug",
            markdown_content="# dup",
            owner="abiolaks",
            repo="blocker_doc_and_solution_bot",
            github_token="fake-token",
            http_client=mock_http,
        )


def test_commit_document_raises_on_401_unauthorized() -> None:
    """If GitHub returns 401, raise PermissionError."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"message": "Bad credentials"}
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with pytest.raises(PermissionError, match="invalid or expired"):
        commit_document(
            project="p",
            title_slug="slug",
            markdown_content="# test",
            owner="abiolaks",
            repo="blocker_doc_and_solution_bot",
            github_token="fake-token",
            http_client=mock_http,
        )


def test_commit_document_reads_token_from_env() -> None:
    """When no github_token is passed, commit_document should read GITHUB_PAT from env."""
    from blocker_doc_and_solution_bot.github_commit.committer import commit_document

    mock_http = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "content": {"html_url": "https://github.com/url", "path": "kb/x/file.md"}
    }
    mock_http.put.return_value = mock_response
    mock_http.__enter__.return_value = mock_http
    mock_http.__exit__.return_value = None

    with patch.dict("os.environ", {"GITHUB_PAT": "env-token-abc"}):
        commit_document(
            project="p",
            title_slug="slug",
            markdown_content="# test",
            owner="abiolaks",
            repo="blocker_doc_and_solution_bot",
            http_client=mock_http,
        )

    # Verify the auth header was set with the env token
    call_args = mock_http.put.call_args
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer env-token-abc"


# ---------------------------------------------------------------------------
# Integration tests: FastAPI /save endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_mocked_commit() -> Generator[TestClient, None, None]:
    """Create a TestClient with commit_document patched to return a known URL."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with patch(
        "blocker_doc_and_solution_bot.search_api.app.commit_document",
        return_value="https://github.com/abiolaks/repo/blob/main/knowledge-base/p/file.md",
    ):
        yield TestClient(app)


def test_save_endpoint_returns_200_with_url(client_with_mocked_commit: TestClient) -> None:
    """POST /save should return 200 with the committed file URL and path."""
    payload = {
        "project": "my-project",
        "title_slug": "some-issue",
        "markdown": "# My Issue\n\n## Problem\nError occurred",
    }
    response = client_with_mocked_commit.post("/save", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://github.com/abiolaks/repo/blob/main/knowledge-base/p/file.md"
    assert "path" in data


def test_save_endpoint_rejects_missing_fields(
    client_with_mocked_commit: TestClient,
) -> None:
    """POST /save should reject requests with missing required fields."""
    response = client_with_mocked_commit.post(
        "/save", json={"project": "only project"}
    )
    assert response.status_code == 422


def test_save_endpoint_rejects_empty_project(
    client_with_mocked_commit: TestClient,
) -> None:
    """POST /save should reject requests with empty project field."""
    response = client_with_mocked_commit.post(
        "/save",
        json={"project": "", "title_slug": "slug", "markdown": "# md"},
    )
    assert response.status_code == 422


def test_save_endpoint_triggers_incremental_index_update() -> None:
    """POST /save should call add_document_to_index after a successful commit."""
    from blocker_doc_and_solution_bot.search_api.app import app

    with (
        patch(
            "blocker_doc_and_solution_bot.search_api.app._openai_client",
            MagicMock(),
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app._blob_client",
            MagicMock(),
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.commit_document",
            return_value="https://github.com/abiolaks/repo/blob/main/knowledge-base/p/file.md",
        ),
        patch(
            "blocker_doc_and_solution_bot.search_api.app.add_document_to_index",
        ) as mock_add,
    ):
        client = TestClient(app)
        payload = {
            "project": "my-project",
            "title_slug": "some-issue",
            "markdown": "# My Issue\n\n## Problem\nError occurred",
        }
        response = client.post("/save", json=payload)
        assert response.status_code == 200

        mock_add.assert_called_once()
        call_kwargs = mock_add.call_args.kwargs
        assert call_kwargs["document_content"] == payload["markdown"]
        assert "knowledge-base/my-project/" in call_kwargs["document_path"]
        assert call_kwargs["document_path"].endswith("-some-issue.md")
