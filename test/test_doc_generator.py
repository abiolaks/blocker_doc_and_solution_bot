"""Tests for Groq-powered document generation module and /generate-doc endpoint."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: generate_document function
# ---------------------------------------------------------------------------


def test_generate_document_calls_llm_and_returns_string() -> None:
    """generate_document should call the LLM client and return a non-empty string."""
    from blocker_doc_and_solution_bot.doc_generator.generator import generate_document

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(message=MagicMock(content="# Test Title\n\n## Problem\n\nSome problem"))
        ]
    )

    answers = {
        "error": "ModuleNotFoundError in pipeline",
        "solution": "pip install missing-package",
        "project": "project-alpha",
    }

    result = generate_document(answers, llm_client=mock_client)

    assert isinstance(result, str)
    assert len(result) > 0
    mock_client.chat.completions.create.assert_called_once()


def test_system_prompt_enforces_template_sections() -> None:
    """The system prompt sent to the LLM must require all template sections."""
    from blocker_doc_and_solution_bot.doc_generator.generator import generate_document

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Title\n\n## Problem\n..."))]
    )

    answers = {"error": "Some error", "solution": "Some fix", "project": "test-proj"}
    generate_document(answers, llm_client=mock_client)

    call_args = mock_client.chat.completions.create.call_args
    system_prompt: str = call_args.kwargs["messages"][0]["content"]

    required_sections = [
        "## Problem",
        "## Root Cause",
        "## Solution",
        "## Environment",
        "## Tags",
        "## Metadata",
    ]
    for section in required_sections:
        assert section in system_prompt, (
            f"System prompt missing required section: {section}"
        )


def test_system_prompt_requires_non_static_title() -> None:
    """The system prompt must instruct the LLM to generate a real title, not a placeholder."""
    from blocker_doc_and_solution_bot.doc_generator.generator import generate_document

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Ok"))]
    )

    generate_document(
        {"error": "err", "solution": "fix", "project": "p"},
        llm_client=mock_client,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_prompt: str = call_kwargs["messages"][0]["content"]
    assert "auto-generated" in system_prompt
    assert "static placeholder" in system_prompt


def test_system_prompt_requires_non_empty_tags() -> None:
    """The system prompt must instruct the LLM to infer tags, not leave them empty."""
    from blocker_doc_and_solution_bot.doc_generator.generator import generate_document

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Ok"))]
    )

    generate_document(
        {"error": "err", "solution": "fix", "project": "p"},
        llm_client=mock_client,
    )

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    system_prompt: str = call_kwargs["messages"][0]["content"]
    assert "Do NOT leave Tags empty" in system_prompt


def test_generate_document_reads_api_key_from_env() -> None:
    """When no llm_client is passed, generate_document should read GROQ_API_KEY from env."""
    from unittest.mock import patch

    from blocker_doc_and_solution_bot.doc_generator.generator import generate_document

    mock_groq_cls = MagicMock()
    mock_groq_cls.return_value.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="# Test"))]
    )

    answers = {"error": "err", "solution": "fix", "project": "p"}

    with patch(
        "blocker_doc_and_solution_bot.doc_generator.generator.Groq", mock_groq_cls
    ), patch.dict("os.environ", {"GROQ_API_KEY": "test-key-123"}):
        result = generate_document(answers)

    assert result == "# Test"
    mock_groq_cls.assert_called_once_with(api_key="test-key-123")


# ---------------------------------------------------------------------------
# Integration tests: FastAPI /generate-doc endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def client_with_mocked_groq() -> Generator[TestClient, None, None]:
    """Create a TestClient with the Groq client patched to return known output."""
    mock_groq = MagicMock()
    mock_groq.return_value.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content=(
                        "# ModuleNotFoundError Fix\n\n"
                        "## Problem\nModuleNotFoundError in pipeline\n\n"
                        "## Root Cause\nMissing dependency\n\n"
                        "## Solution\npip install missing-package\n\n"
                        "## Environment\nPython 3.13\n\n"
                        "## Tags\npip, dependencies, import\n\n"
                        "## Metadata\nProject: project-alpha\n"
                    )
                )
            )
        ]
    )

    with patch(
        "blocker_doc_and_solution_bot.doc_generator.generator.Groq", mock_groq
    ), patch.dict("os.environ", {"GROQ_API_KEY": "fake-key"}):
        from blocker_doc_and_solution_bot.search_api.app import app

        yield TestClient(app)


def test_generate_doc_endpoint_returns_200(client_with_mocked_groq: TestClient) -> None:
    """POST /generate-doc should return 200 with valid markdown JSON."""
    payload = {
        "error": "ModuleNotFoundError in pipeline",
        "solution": "pip install missing-package",
        "project": "project-alpha",
    }
    response = client_with_mocked_groq.post("/generate-doc", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "markdown" in data
    assert isinstance(data["markdown"], str)
    assert len(data["markdown"]) > 0
    assert "ModuleNotFoundError Fix" in data["markdown"]


def test_generate_doc_endpoint_rejects_missing_fields(
    client_with_mocked_groq: TestClient,
) -> None:
    """POST /generate-doc should reject requests with missing required fields."""
    response = client_with_mocked_groq.post(
        "/generate-doc", json={"error": "only error"}
    )
    assert response.status_code == 422


def test_generate_doc_endpoint_rejects_empty_error(
    client_with_mocked_groq: TestClient,
) -> None:
    """POST /generate-doc should reject requests with empty error field."""
    response = client_with_mocked_groq.post(
        "/generate-doc",
        json={"error": "", "solution": "fix", "project": "proj"},
    )
    assert response.status_code == 422
