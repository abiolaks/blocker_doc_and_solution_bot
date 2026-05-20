"""Tests for FastAPI search endpoint and search logic."""

from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import faiss
import numpy as np
import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Unit tests: search logic functions
# ---------------------------------------------------------------------------


def test_classify_tier_match() -> None:
    """Scores > 0.85 should be classified as 'match'."""
    from blocker_doc_and_solution_bot.search_api.search import classify_tier

    assert classify_tier(0.95) == "match"
    assert classify_tier(0.86) == "match"
    assert classify_tier(0.851) == "match"


def test_classify_tier_related() -> None:
    """Scores 0.5–0.85 should be classified as 'related'."""
    from blocker_doc_and_solution_bot.search_api.search import classify_tier

    assert classify_tier(0.85) == "related"
    assert classify_tier(0.70) == "related"
    assert classify_tier(0.50) == "related"


def test_classify_tier_no_match() -> None:
    """Scores < 0.5 should be classified as 'no_match'."""
    from blocker_doc_and_solution_bot.search_api.search import classify_tier

    assert classify_tier(0.49) == "no_match"
    assert classify_tier(0.0) == "no_match"


def test_search_and_resolve_returns_tiered_results() -> None:
    """search_and_resolve should search the index and return tiered paths with scores."""
    from blocker_doc_and_solution_bot.search_api.search import search_and_resolve

    # Build a tiny FAISS index with 3 vectors
    dim = 1536
    index = faiss.IndexFlatIP(dim)
    vectors = np.random.rand(3, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    index_map = {
        "0": "knowledge-base/proj-a/doc1.md",
        "1": "knowledge-base/proj-b/doc2.md",
        "2": "knowledge-base/proj-c/doc3.md",
    }

    # Search with a vector close to doc0
    query_vec = vectors[0:1].copy()
    results = search_and_resolve(query_vec, index, index_map, top_k=3)

    assert len(results) > 0
    for r in results:
        assert "score" in r
        assert "path" in r
        assert "tier" in r
        assert r["tier"] in ("match", "related", "no_match")


def test_search_and_resolve_respects_top_k() -> None:
    """search_and_resolve should return at most top_k results."""
    from blocker_doc_and_solution_bot.search_api.search import search_and_resolve

    dim = 1536
    index = faiss.IndexFlatIP(dim)
    vectors = np.random.rand(5, dim).astype(np.float32)
    faiss.normalize_L2(vectors)
    index.add(vectors)

    index_map = {str(i): f"kb/doc{i}.md" for i in range(5)}
    query_vec = np.random.rand(1, dim).astype(np.float32)
    faiss.normalize_L2(query_vec)

    results = search_and_resolve(query_vec, index, index_map, top_k=2)
    assert len(results) == 2


def test_embed_query_returns_normalized_vector() -> None:
    """embed_query should return a normalized 1536-dim vector."""
    from blocker_doc_and_solution_bot.search_api.search import embed_query

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[1.0] + [0.0] * 1535)]
    )

    vec = embed_query("test query", mock_client)

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (1, 1536)
    # Should be L2-normalized (unit vector)
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-5


def test_load_index_from_blob(tmp_path: Path) -> None:
    """load_index_from_blob should download and load FAISS index and index_map."""
    from blocker_doc_and_solution_bot.search_api.search import load_index_from_blob

    # Build a real FAISS index and upload simulation
    dim = 1536
    index = faiss.IndexFlatIP(dim)
    vectors = np.random.rand(3, dim).astype(np.float32)
    index.add(vectors)

    index_path = tmp_path / "faiss.index"
    map_path = tmp_path / "index_map.json"
    faiss.write_index(index, str(index_path))
    map_path.write_text(json.dumps({"0": "path/a.md", "1": "path/b.md", "2": "path/c.md"}))

    # Mock blob client that returns download streams
    mock_blob = MagicMock()

    def make_blob_client(file_path: Path) -> MagicMock:
        blob_client = MagicMock()
        mock_stream = MagicMock()
        mock_stream.readall.return_value = file_path.read_bytes()
        blob_client.download_blob.return_value = mock_stream
        return blob_client

    mock_index_client = make_blob_client(index_path)
    mock_map_client = make_blob_client(map_path)

    mock_blob.get_blob_client.side_effect = lambda container, blob: {
        "faiss.index": mock_index_client,
        "index_map.json": mock_map_client,
    }[blob]

    loaded_index, loaded_map = load_index_from_blob(mock_blob, "test-container")

    assert loaded_index.ntotal == 3
    assert loaded_map == {"0": "path/a.md", "1": "path/b.md", "2": "path/c.md"}


# ---------------------------------------------------------------------------
# Integration tests: FastAPI endpoint
# ---------------------------------------------------------------------------


@pytest.fixture
def app_with_mocks() -> Generator[TestClient, None, None]:
    """Create a TestClient with mocked blob, OpenAI, and FAISS index."""
    from unittest.mock import patch

    dim = 1536
    faiss_index = faiss.IndexFlatIP(dim)
    test_vectors = np.random.rand(5, dim).astype(np.float32)
    faiss.normalize_L2(test_vectors)
    faiss_index.add(test_vectors)

    index_map = {str(i): f"kb/doc{i}.md" for i in range(5)}

    mock_openai = MagicMock()
    mock_blob = MagicMock()

    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=test_vectors[0].tolist())]
    )

    with patch(
        "blocker_doc_and_solution_bot.search_api.app._openai_client", mock_openai
    ), patch(
        "blocker_doc_and_solution_bot.search_api.app._blob_client", mock_blob
    ), patch(
        "blocker_doc_and_solution_bot.search_api.app._faiss_index", faiss_index
    ), patch(
        "blocker_doc_and_solution_bot.search_api.app._index_map", index_map
    ):
        from blocker_doc_and_solution_bot.search_api.app import app

        yield TestClient(app)


def test_search_endpoint_returns_200(app_with_mocks: TestClient) -> None:
    """POST /search should return 200 with tiered results."""
    response = app_with_mocks.post("/search", json={"query": "how to fix blob trigger?"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    for r in data["results"]:
        assert "tier" in r
        assert "score" in r
        assert "path" in r


def test_search_endpoint_rejects_empty_query(app_with_mocks: TestClient) -> None:
    """POST /search should reject empty query strings."""
    response = app_with_mocks.post("/search", json={"query": ""})
    assert response.status_code == 422


def test_search_endpoint_rejects_missing_query(app_with_mocks: TestClient) -> None:
    """POST /search should reject requests without a query field."""
    response = app_with_mocks.post("/search", json={})
    assert response.status_code == 422
