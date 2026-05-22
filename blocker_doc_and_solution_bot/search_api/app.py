"""FastAPI search endpoint — loads FAISS index from blob, serves /search."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import faiss
import numpy as np
from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableClient, TableServiceClient
from azure.storage.blob import BlobServiceClient
from botbuilder.schema import Activity
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from openai import OpenAI
from pydantic import BaseModel, Field

from blocker_doc_and_solution_bot.doc_generator.generator import generate_document
from blocker_doc_and_solution_bot.github_commit.committer import commit_document
from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index
from blocker_doc_and_solution_bot.search_api.search import (
    embed_query,
    load_index_from_blob,
    search_and_resolve,
)
from blocker_doc_and_solution_bot.teams_bot.bot import SupportBot, create_adapter
from blocker_doc_and_solution_bot.telegram_bot.bot import (
    handle_telegram_update,
    register_webhook,
)

# Module-level state — initialized eagerly at import time.
# We don't rely on FastAPI's lifespan because Azure Functions' AsgiMiddleware
# does not drive ASGI lifespan events. Each request is handled in isolation.
_openai_client: OpenAI | None = None
_blob_client: BlobServiceClient | None = None
_faiss_index: faiss.Index | None = None
_index_map: dict[str, str] = {}
_session_table: TableClient | None = None
_analytics_table: TableClient | None = None


def _ensure_table(storage_conn_str: str, table_name: str) -> TableClient | None:
    """Get a TableClient, creating the table in Azure Table Storage if it doesn't exist."""
    try:
        service = TableServiceClient.from_connection_string(storage_conn_str)
        try:
            service.create_table(table_name)
        except ResourceExistsError:
            pass
        return service.get_table_client(table_name)
    except Exception as exc:  # noqa: BLE001
        print(f"[startup] failed to get/create table {table_name!r}: {exc!r}")
        return None


def _initialize_state() -> None:
    """Initialize module-level clients and load the FAISS index from blob.

    Runs once at module import. Failures are logged but do not raise — endpoints
    will return 503 instead of crashing the function host.
    """
    global _openai_client, _blob_client, _faiss_index, _index_map
    global _session_table, _analytics_table

    load_dotenv()

    try:
        openai_api_key = os.environ["OPENAI_API_KEY"]
        openai_endpoint = os.environ["OPENAI_ENDPOINT"]
        storage_conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    except KeyError as exc:
        print(f"[startup] missing required env var: {exc}; endpoints will return 503")
        return

    container = os.getenv("AZURE_STORAGE_CONTAINER", "faiss-index")
    session_table_name = os.getenv("AZURE_SESSION_TABLE", "botsessions")
    analytics_table_name = os.getenv("AZURE_ANALYTICS_TABLE", "botanalytics")

    try:
        _openai_client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)
        _blob_client = BlobServiceClient.from_connection_string(storage_conn_str)
        _faiss_index, _index_map = load_index_from_blob(_blob_client, container)
        print(f"[startup] FAISS index loaded: {_faiss_index.ntotal} vectors")
    except Exception as exc:  # noqa: BLE001 — log and continue, don't crash host
        print(f"[startup] failed to initialize search backend: {exc!r}")
        return

    _session_table = _ensure_table(storage_conn_str, session_table_name)
    _analytics_table = _ensure_table(storage_conn_str, analytics_table_name)
    print(
        f"[startup] tables: sessions={'ok' if _session_table else 'fail'}, "
        f"analytics={'ok' if _analytics_table else 'fail'}"
    )

    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        func_base = os.getenv("AZURE_FUNCTION_BASE_URL", "")
        if func_base:
            webhook_url = f"{func_base}/api/telegram/webhook"
            ok = register_webhook(telegram_token, webhook_url)
            print(f"[startup] telegram webhook registration: {'ok' if ok else 'failed'}")


_initialize_state()


app = FastAPI(title="Support Bot Search API")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The blocker/error description to search for")


class SearchResult(BaseModel):
    score: float
    path: str
    tier: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


class GenerateDocRequest(BaseModel):
    error: str = Field(..., min_length=1, description="The error or unexpected behavior")
    solution: str = Field(..., min_length=1, description="Steps taken to resolve the issue")
    project: str = Field(
        ..., min_length=1, description="Project name for the knowledge base folder"
    )


class GenerateDocResponse(BaseModel):
    markdown: str


class SaveRequest(BaseModel):
    project: str = Field(..., min_length=1, description="Project folder name under knowledge-base/")
    title_slug: str = Field(..., min_length=1, description="URL-safe short slug for the filename")
    markdown: str = Field(..., min_length=1, description="Full Markdown content of the document")


class SaveResponse(BaseModel):
    url: str
    path: str


@app.post("/api/search", response_model=SearchResponse)
def search(request: SearchRequest) -> dict[str, Any]:
    """Embed the query, search FAISS index, and return tiered results."""
    if _openai_client is None or _faiss_index is None:
        raise HTTPException(status_code=503, detail="Search index not loaded")

    query_vec: np.ndarray = embed_query(request.query, _openai_client)
    raw_results = search_and_resolve(query_vec, _faiss_index, _index_map, top_k=3)

    if not raw_results:
        return {"results": []}

    return {"results": raw_results}


@app.post("/api/generate-doc", response_model=GenerateDocResponse)
def generate_doc(request: GenerateDocRequest) -> dict[str, str]:
    """Generate a structured Markdown knowledge base entry from user answers."""
    answers: dict[str, str] = {
        "error": request.error,
        "solution": request.solution,
        "project": request.project,
    }
    markdown = generate_document(answers)
    return {"markdown": markdown}


@app.post("/api/save", response_model=SaveResponse)
def save_document(request: SaveRequest) -> dict[str, str]:
    """Commit an approved Markdown document to the GitHub knowledge base."""
    owner = os.getenv("GITHUB_REPO_OWNER", "abiolaks")
    repo = os.getenv("GITHUB_REPO_NAME", "blocker_doc_and_solution_bot")

    try:
        url = commit_document(
            project=request.project,
            title_slug=request.title_slug,
            markdown_content=request.markdown,
            owner=owner,
            repo=repo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc))

    filename = f"{datetime.now().strftime('%Y-%m-%d')}-{request.title_slug}.md"
    path = f"knowledge-base/{request.project}/{filename}"

    # Trigger incremental FAISS index update
    container = os.getenv("AZURE_STORAGE_CONTAINER", "faiss-index")
    if _openai_client is not None and _blob_client is not None:
        add_document_to_index(
            document_content=request.markdown,
            document_path=path,
            openai_client=_openai_client,
            blob_client=_blob_client,
            container_name=container,
        )

    return {"url": url, "path": path}


@app.post("/api/messages")
async def teams_messages(request: Request) -> Response:
    """Azure Bot Service messaging endpoint for Microsoft Teams.

    Receives Activities from the Bot Framework Service, authenticates
    via the Authorization header, and delegates to the SupportBot handler.

    Dependencies (OpenAI client, FAISS index, analytics table) are injected
    from module-level state into the bot at request time.
    """
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    adapter = create_adapter()
    bot = SupportBot(
        openai_client=_openai_client,
        faiss_index=_faiss_index,
        index_map=_index_map,
        analytics_table=_analytics_table,
    )

    invoke_response = await adapter.process_activity(activity, auth_header, bot.on_turn)
    if invoke_response is not None:
        body = invoke_response.body
        content = json.dumps(body) if body is not None else ""
        return Response(
            content=content,
            status_code=invoke_response.status,
            media_type="application/json",
        )
    return Response(status_code=200)


@app.post("/api/telegram/webhook")
def telegram_webhook(update: dict[str, Any]) -> dict[str, str]:
    """Receive Telegram webhook updates — extract text, search, and reply in-thread."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")

    if _openai_client is None or _faiss_index is None:
        raise HTTPException(status_code=503, detail="Search index not loaded")

    handle_telegram_update(
        update,
        bot_token=token,
        table_client=_session_table,
    )
    return {"status": "ok"}
