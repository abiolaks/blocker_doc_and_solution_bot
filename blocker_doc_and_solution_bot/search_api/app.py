"""FastAPI search endpoint — loads FAISS index from blob, serves /search."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import faiss
import numpy as np
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field

from blocker_doc_and_solution_bot.doc_generator.generator import generate_document
from blocker_doc_and_solution_bot.search_api.search import (
    embed_query,
    load_index_from_blob,
    search_and_resolve,
)

# Module-level state initialized at startup
_openai_client: OpenAI | None = None
_blob_client: BlobServiceClient | None = None
_faiss_index: faiss.Index | None = None
_index_map: dict[str, str] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Load FAISS index and index_map from Azure Blob Storage on startup."""
    global _openai_client, _blob_client, _faiss_index, _index_map

    load_dotenv()

    openai_api_key = os.environ["OPENAI_API_KEY"]
    openai_endpoint = os.environ["OPENAI_ENDPOINT"]
    storage_conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container = os.getenv("AZURE_STORAGE_CONTAINER", "faiss-index")

    _openai_client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)
    _blob_client = BlobServiceClient.from_connection_string(storage_conn_str)

    _faiss_index, _index_map = load_index_from_blob(_blob_client, container)
    yield


app = FastAPI(title="Support Bot Search API", lifespan=lifespan)


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


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> dict[str, Any]:
    """Embed the query, search FAISS index, and return tiered results."""
    if _openai_client is None or _faiss_index is None:
        raise HTTPException(status_code=503, detail="Search index not loaded")

    query_vec: np.ndarray = embed_query(request.query, _openai_client)
    raw_results = search_and_resolve(query_vec, _faiss_index, _index_map, top_k=3)

    if not raw_results:
        return {"results": []}

    return {"results": raw_results}


@app.post("/generate-doc", response_model=GenerateDocResponse)
def generate_doc(request: GenerateDocRequest) -> dict[str, str]:
    """Generate a structured Markdown knowledge base entry from user answers."""
    answers: dict[str, str] = {
        "error": request.error,
        "solution": request.solution,
        "project": request.project,
    }
    markdown = generate_document(answers)
    return {"markdown": markdown}
