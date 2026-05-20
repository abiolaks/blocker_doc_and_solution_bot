"""Core search logic — embed, search FAISS, resolve paths, classify tiers."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import faiss
import numpy as np
from azure.storage.blob import BlobServiceClient
from openai import OpenAI


def classify_tier(score: float) -> str:
    """Classify a similarity score into a search tier.

    - > 0.85: 'match' (high confidence)
    - 0.5–0.85: 'related'
    - < 0.5: 'no_match'
    """
    if score > 0.85:
        return "match"
    if score >= 0.5:
        return "related"
    return "no_match"


def embed_query(query: str, openai_client: OpenAI) -> np.ndarray:
    """Embed a query string and return a normalized vector of shape (1, 1536)."""
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[query],
    )
    vec = np.array([response.data[0].embedding], dtype=np.float32)
    faiss.normalize_L2(vec)
    return vec


def search_and_resolve(
    query_vec: np.ndarray,
    faiss_index: faiss.Index,
    index_map: dict[str, str],
    top_k: int = 3,
) -> list[dict[str, str | float]]:
    """Search the FAISS index and resolve integer IDs to GitHub file paths.

    Returns a list of dicts with 'score', 'path', and 'tier' keys.
    """
    distances, indices = faiss_index.search(query_vec, top_k)

    results: list[dict[str, str | float]] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        score = float(dist)
        path = index_map.get(str(idx), "")
        tier = classify_tier(score)
        results.append({"score": score, "path": path, "tier": tier})

    return results


def load_index_from_blob(
    blob_client: BlobServiceClient,
    container_name: str,
) -> tuple[faiss.Index, dict[str, str]]:
    """Download and load the FAISS index and index_map from Azure Blob Storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Download faiss.index
        index_blob = blob_client.get_blob_client(
            container=container_name, blob="faiss.index"
        )
        index_path = tmp / "faiss.index"
        with index_path.open("wb") as f:
            stream = index_blob.download_blob()
            f.write(stream.readall())

        # Download index_map.json
        map_blob = blob_client.get_blob_client(
            container=container_name, blob="index_map.json"
        )
        map_path = tmp / "index_map.json"
        with map_path.open("wb") as f:
            stream = map_blob.download_blob()
            f.write(stream.readall())

        faiss_index = faiss.read_index(str(index_path))
        index_map: dict[str, str] = json.loads(map_path.read_text())

    return faiss_index, index_map
