"""FAISS index builder — collects docs, embeds, builds index, uploads to Blob."""

from __future__ import annotations

import json
import os
from pathlib import Path

import faiss
import numpy as np
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from openai import OpenAI


def collect_documents(kb_dir: Path) -> list[dict[str, str]]:
    """Recursively find all .md files under kb_dir and return their paths and contents."""
    docs: list[dict[str, str]] = []
    for md_file in sorted(kb_dir.rglob("*.md")):
        if not md_file.is_file():
            continue
        docs.append({
            "path": str(md_file),
            "content": md_file.read_text(),
        })
    return docs


def embed_documents(
    docs: list[dict[str, str]], openai_client: OpenAI
) -> np.ndarray:
    """Embed each document's content using text-embedding-3-small.

    Returns a 2D numpy array of shape (n_docs, 1536).
    """
    if not docs:
        return np.empty((0, 1536), dtype=np.float32)

    texts = [doc["content"] for doc in docs]
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    vectors = [item.embedding for item in response.data]
    return np.array(vectors, dtype=np.float32)


def build_index(
    embeddings: np.ndarray, output_path: Path
) -> faiss.Index | None:
    """Build a FAISS index from embeddings and save to output_path.

    Returns the index, or None if embeddings is empty.
    """
    if embeddings.shape[0] == 0:
        return None

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    faiss.write_index(index, str(output_path))
    return index


def create_index_map(docs: list[dict[str, str]]) -> dict[str, str]:
    """Map FAISS integer IDs to source file paths."""
    return {str(i): doc["path"] for i, doc in enumerate(docs)}


def upload_to_blob(
    blob_client: BlobServiceClient,
    index_path: Path,
    map_path: Path,
    container_name: str,
) -> None:
    """Upload faiss.index and index_map.json to Azure Blob Storage."""
    index_blob = blob_client.get_blob_client(
        container=container_name, blob="faiss.index"
    )
    with index_path.open("rb") as f:
        index_blob.upload_blob(f, overwrite=True)

    map_blob = blob_client.get_blob_client(
        container=container_name, blob="index_map.json"
    )
    with map_path.open("rb") as f:
        map_blob.upload_blob(f, overwrite=True)


def rebuild_index(
    kb_dir: Path,
    openai_client: OpenAI,
    blob_client: BlobServiceClient,
    container_name: str,
    *,
    index_path: Path | None = None,
    map_path: Path | None = None,
) -> faiss.Index | None:
    """Full rebuild: collect docs, embed, build index, create map, upload to blob.

    Returns the FAISS index, or None if no documents were found.
    """
    docs = collect_documents(kb_dir)
    if not docs:
        return None

    embeddings = embed_documents(docs, openai_client)

    index_path = index_path or Path("faiss.index")
    map_path = map_path or Path("index_map.json")

    index = build_index(embeddings, index_path)
    if index is None:
        return None

    index_map = create_index_map(docs)
    map_path.write_text(json.dumps(index_map, indent=2))

    upload_to_blob(blob_client, index_path, map_path, container_name)

    return index


def main() -> None:
    """Entry point for manual full-rebuild operation."""
    load_dotenv()

    kb_dir = Path(os.getenv("KNOWLEDGE_BASE_DIR", "Knowledge_base"))
    container = os.getenv("AZURE_STORAGE_CONTAINER", "faiss-index")
    openai_api_key = os.environ["OPENAI_API_KEY"]
    openai_endpoint = os.environ["OPENAI_ENDPOINT"]
    storage_conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

    openai_client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_endpoint,
    )
    blob_client = BlobServiceClient.from_connection_string(storage_conn_str)

    index = rebuild_index(
        kb_dir=kb_dir,
        openai_client=openai_client,
        blob_client=blob_client,
        container_name=container,
    )

    if index is None:
        print("No documents found in knowledge base.")
    else:
        print(f"Index built with {index.ntotal} documents.")


if __name__ == "__main__":
    main()
