"""Incremental FAISS index update — embed a new document, add to existing index, upload back."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import faiss
import numpy as np
from azure.storage.blob import BlobServiceClient
from openai import OpenAI


def add_document_to_index(
    document_content: str,
    document_path: str,
    *,
    openai_client: OpenAI,
    blob_client: BlobServiceClient,
    container_name: str,
    next_id: int | None = None,
) -> dict[str, object]:
    """Add a single document to the existing FAISS index in Azure Blob Storage.

    Downloads the current index and index_map from blob, embeds the new document,
    adds the vector to the FAISS index, appends the mapping entry, and uploads
    both files back.

    Args:
        document_content: Full Markdown content of the new document.
        document_path: GitHub file path for the new document
            (e.g., "knowledge-base/my-project/doc.md").
        openai_client: OpenAI client for text-embedding-3-small.
        blob_client: Azure BlobServiceClient for storage.
        container_name: Azure Blob Storage container name.
        next_id: FAISS ID for the new document. Defaults to len(index_map).

    Returns:
        Dictionary with ntotal (int), faiss_id (int), index_map (dict[str, str]).
    """
    # 1. Download existing index and map from blob
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        index_blob = blob_client.get_blob_client(
            container=container_name, blob="faiss.index"
        )
        index_path = tmp / "faiss.index"
        with index_path.open("wb") as f:
            stream = index_blob.download_blob()
            f.write(stream.readall())

        map_blob = blob_client.get_blob_client(
            container=container_name, blob="index_map.json"
        )
        map_path = tmp / "index_map.json"
        with map_path.open("wb") as f:
            stream = map_blob.download_blob()
            f.write(stream.readall())

        faiss_index = faiss.read_index(str(index_path))
        index_map: dict[str, str] = json.loads(map_path.read_text())

    # 2. Embed the new document content
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=[document_content],
    )
    vec = np.array([response.data[0].embedding], dtype=np.float32)

    # 3. Add to FAISS index
    faiss_index.add(vec)

    # 4. Append to index_map
    new_id = next_id if next_id is not None else len(index_map)
    index_map[str(new_id)] = document_path

    # 5. Save and upload back to blob
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        updated_index_path = tmp / "faiss.index"
        updated_map_path = tmp / "index_map.json"

        faiss.write_index(faiss_index, str(updated_index_path))
        updated_map_path.write_text(json.dumps(index_map))

        upload_index_blob = blob_client.get_blob_client(
            container=container_name, blob="faiss.index"
        )
        with updated_index_path.open("rb") as f:
            upload_index_blob.upload_blob(f, overwrite=True)

        upload_map_blob = blob_client.get_blob_client(
            container=container_name, blob="index_map.json"
        )
        with updated_map_path.open("rb") as f:
            upload_map_blob.upload_blob(f, overwrite=True)

    return {
        "ntotal": faiss_index.ntotal,
        "faiss_id": new_id,
        "index_map": index_map,
    }
