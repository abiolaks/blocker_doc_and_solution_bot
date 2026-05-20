"""Document generation module — wraps Groq LLM calls behind a single interface."""

from __future__ import annotations

from typing import Any

from groq import Groq


def generate_document(answers: dict[str, str], *, llm_client: Any = None) -> str:
    """Generate structured Markdown from user Q&A responses.

    Args:
        answers: dict with 'error', 'solution', 'project' keys.
        llm_client: Optional LLM client (Groq or OpenAI-compatible). If None,
            creates a default Groq client using GROQ_API_KEY env var.

    Returns:
        Generated Markdown string following the knowledge base template.
    """
    if llm_client is None:
        import os

        llm_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    response = llm_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a technical documentation assistant for a Data Science team. "
                    "Generate a structured Markdown knowledge base entry from the user's answers. "
                    "Follow this template exactly:\n\n"
                    "# Title\n"
                    "Short issue summary auto-generated from the error description\n\n"
                    "## Problem\n"
                    "Error or unexpected behavior that occurred\n\n"
                    "## Root Cause\n"
                    "Plain-language explanation of why the error happened\n\n"
                    "## Solution\n"
                    "Steps taken and code snippets used to resolve the issue\n\n"
                    "## Environment\n"
                    "Tools, versions, and dependencies in use (if known)\n\n"
                    "## Tags\n"
                    "Relevant keywords inferred from the error and solution (comma-separated)\n\n"
                    "## Metadata\n"
                    "Author, date, and project name\n\n"
                    "Do NOT use a static placeholder title — generate a real title from the error. "
                    "Do NOT leave Tags empty — infer tags from the content. "
                    "Include the project name in the Metadata section."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Error: {answers['error']}\n"
                    f"Solution: {answers['solution']}\n"
                    f"Project: {answers['project']}"
                ),
            },
        ],
    )
    return str(response.choices[0].message.content)
