"""Tests for incremental FAISS index updater module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import faiss
import numpy as np

# ---------------------------------------------------------------------------
# Unit tests: add_document_to_index function
# ---------------------------------------------------------------------------


def test_add_document_to_index_increases_ntotal(tmp_path: Path) -> None:
    """Adding one document should increase ntotal by 1."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    # Build a pre-existing index with 3 documents
    existing_index = faiss.IndexFlatIP(dim)
    existing_vectors = np.random.rand(3, dim).astype(np.float32)
    existing_index.add(existing_vectors)
    existing_map = {"0": "kb/proj-a/doc0.md", "1": "kb/proj-b/doc1.md", "2": "kb/proj-c/doc2.md"}

    # Save to temp files (simulating what's in blob)
    index_path = tmp_path / "faiss.index"
    map_path = tmp_path / "index_map.json"
    faiss.write_index(existing_index, str(index_path))
    map_path.write_text(json.dumps(existing_map))

    # Mock blob client to return our temp files
    mock_blob = MagicMock()

    def make_download_client(file_path: Path) -> MagicMock:
        client = MagicMock()
        stream = MagicMock()
        stream.readall.return_value = file_path.read_bytes()
        client.download_blob.return_value = stream
        return client

    def make_upload_client(file_path: Path) -> MagicMock:
        captured_data: list[bytes] = []

        class FakeUploadClient:
            @staticmethod
            def upload_blob(data: bytes, overwrite: bool = False) -> None:  # noqa: FBT001, FBT002
                captured_data.append(data)

            @property
            def uploaded_bytes(self) -> bytes:
                return captured_data[0] if captured_data else b""

        client = FakeUploadClient()
        return client  # type: ignore[return-value]

    index_dl_client = make_download_client(index_path)
    map_dl_client = make_download_client(map_path)

    mock_blob.get_blob_client.side_effect = lambda container, blob: {
        ("test-container", "faiss.index"): index_dl_client,
        ("test-container", "index_map.json"): map_dl_client,
    }[container, blob]

    # Mock OpenAI to return a known embedding
    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * dim)]
    )

    result = add_document_to_index(
        document_content="# New Doc\n\n## Problem\n...",
        document_path="kb/proj-d/new-doc.md",
        openai_client=mock_openai,
        blob_client=mock_blob,
        container_name="test-container",
    )

    assert result["ntotal"] == 4
    assert result["faiss_id"] == 3
    expected_map = {
        "0": "kb/proj-a/doc0.md",
        "1": "kb/proj-b/doc1.md",
        "2": "kb/proj-c/doc2.md",
        "3": "kb/proj-d/new-doc.md",
    }
    assert result["index_map"] == expected_map


def test_add_document_first_document(tmp_path: Path) -> None:
    """Adding a document to an empty index should work (first document)."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    empty_index = faiss.IndexFlatIP(dim)
    empty_map: dict[str, str] = {}

    index_path = tmp_path / "faiss.index"
    map_path = tmp_path / "index_map.json"
    faiss.write_index(empty_index, str(index_path))
    map_path.write_text(json.dumps(empty_map))

    mock_blob = MagicMock()

    def make_download_client(file_path: Path) -> MagicMock:
        client = MagicMock()
        stream = MagicMock()
        stream.readall.return_value = file_path.read_bytes()
        client.download_blob.return_value = stream
        return client

    index_dl_client = make_download_client(index_path)
    map_dl_client = make_download_client(map_path)

    mock_blob.get_blob_client.side_effect = lambda container, blob: {
        ("test-container", "faiss.index"): index_dl_client,
        ("test-container", "index_map.json"): map_dl_client,
    }[container, blob]

    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * dim)]
    )

    result = add_document_to_index(
        document_content="# First Doc\n\n## Problem\n...",
        document_path="kb/proj/first.md",
        openai_client=mock_openai,
        blob_client=mock_blob,
        container_name="test-container",
    )

    assert result["ntotal"] == 1
    assert result["faiss_id"] == 0
    assert result["index_map"] == {"0": "kb/proj/first.md"}


def test_add_document_embeds_content_correctly() -> None:
    """The document content passed to add_document_to_index should be sent to OpenAI embeddings."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    existing_index = faiss.IndexFlatIP(dim)
    existing_index.add(np.random.rand(1, dim).astype(np.float32))
    existing_map = {"0": "kb/existing.md"}

    # Use separate temp files per test to avoid cross-test interference
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        index_path = tmp / "faiss.index"
        map_path = tmp / "index_map.json"
        faiss.write_index(existing_index, str(index_path))
        map_path.write_text(json.dumps(existing_map))

        mock_blob = MagicMock()

        def make_dl_client(file_path: Path) -> MagicMock:
            client = MagicMock()
            stream = MagicMock()
            stream.readall.return_value = file_path.read_bytes()
            client.download_blob.return_value = stream
            return client

        mock_blob.get_blob_client.side_effect = lambda container, blob: {
            ("test-container", "faiss.index"): make_dl_client(index_path),
            ("test-container", "index_map.json"): make_dl_client(map_path),
        }[container, blob]

        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.5] * dim)]
        )

        add_document_to_index(
            document_content="## Problem\nBlob trigger not firing",
            document_path="kb/proj/blob-fix.md",
            openai_client=mock_openai,
            blob_client=mock_blob,
            container_name="test-container",
        )

        mock_openai.embeddings.create.assert_called_once()
        call_args = mock_openai.embeddings.create.call_args
        assert call_args.kwargs["model"] == "text-embedding-3-small"
        assert call_args.kwargs["input"] == ["## Problem\nBlob trigger not firing"]


def test_add_document_uploads_updated_files_to_blob() -> None:
    """After adding a document, updated index and map should be uploaded to blob."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    existing_index = faiss.IndexFlatIP(dim)
    existing_index.add(np.random.rand(2, dim).astype(np.float32))
    existing_map = {"0": "kb/doc0.md", "1": "kb/doc1.md"}

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        index_path = tmp / "faiss.index"
        map_path = tmp / "index_map.json"
        faiss.write_index(existing_index, str(index_path))
        map_path.write_text(json.dumps(existing_map))

        mock_blob = MagicMock()

        def make_dl_client(file_path: Path) -> MagicMock:
            client = MagicMock()
            stream = MagicMock()
            stream.readall.return_value = file_path.read_bytes()
            client.download_blob.return_value = stream
            return client

        index_dl_client = make_dl_client(index_path)
        map_dl_client = make_dl_client(map_path)
        index_ul_client = MagicMock()
        map_ul_client = MagicMock()

        # get_blob_client called 4 times: 2 downloads first, then 2 uploads.
        # Use a list to serve them in order.
        get_blob_clients = [index_dl_client, map_dl_client, index_ul_client, map_ul_client]
        mock_blob.get_blob_client.side_effect = lambda container, blob: get_blob_clients.pop(0)

        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.3] * dim)]
        )

        add_document_to_index(
            document_content="# New doc",
            document_path="kb/proj-new/doc.md",
            openai_client=mock_openai,
            blob_client=mock_blob,
            container_name="test-container",
        )

        assert mock_blob.get_blob_client.call_count == 4
        assert index_ul_client.upload_blob.called
        assert map_ul_client.upload_blob.called


def test_existing_searches_still_work_after_add(tmp_path: Path) -> None:
    """Existing search results should not be corrupted after adding a document."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    existing_index = faiss.IndexFlatIP(dim)
    doc0_vec = np.random.rand(1, dim).astype(np.float32)
    doc1_vec = np.random.rand(1, dim).astype(np.float32)
    existing_index.add(np.vstack([doc0_vec, doc1_vec]))
    existing_map = {"0": "kb/doc0.md", "1": "kb/doc1.md"}

    # Verify search works before update
    k = 2
    distances_before, indices_before = existing_index.search(doc0_vec, k)
    assert indices_before[0][0] == 0  # doc0 is closest to itself

    # Now add a third document
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        index_path = tmp / "faiss.index"
        map_path = tmp / "index_map.json"
        faiss.write_index(existing_index, str(index_path))
        map_path.write_text(json.dumps(existing_map))

        mock_blob = MagicMock()

        def make_dl_client(file_path: Path) -> MagicMock:
            client = MagicMock()
            stream = MagicMock()
            stream.readall.return_value = file_path.read_bytes()
            client.download_blob.return_value = stream
            return client

        mock_blob.get_blob_client.side_effect = lambda container, blob: {
            ("test-container", "faiss.index"): make_dl_client(index_path),
            ("test-container", "index_map.json"): make_dl_client(map_path),
        }[container, blob]

        mock_openai = MagicMock()
        mock_openai.embeddings.create.return_value = MagicMock(
            data=[MagicMock(embedding=[0.9] * dim)]
        )

        result = add_document_to_index(
            document_content="# Doc 2",
            document_path="kb/doc2.md",
            openai_client=mock_openai,
            blob_client=mock_blob,
            container_name="test-container",
        )

        assert result["ntotal"] == 3
        assert result["faiss_id"] == 2
        idx_map: dict[str, str] = result["index_map"]  # type: ignore[assignment]
        assert idx_map["0"] == "kb/doc0.md"
        assert idx_map["1"] == "kb/doc1.md"
        assert idx_map["2"] == "kb/doc2.md"


def test_add_document_accepts_explicit_next_id(tmp_path: Path) -> None:
    """When next_id is provided, it should be used instead of len(index_map)."""
    from blocker_doc_and_solution_bot.index_updater.updater import add_document_to_index

    dim = 1536
    existing_index = faiss.IndexFlatIP(dim)
    existing_index.add(np.random.rand(2, dim).astype(np.float32))
    existing_map = {"0": "kb/doc0.md", "5": "kb/doc5.md"}  # non-contiguous IDs

    index_path = tmp_path / "faiss.index"
    map_path = tmp_path / "index_map.json"
    faiss.write_index(existing_index, str(index_path))
    map_path.write_text(json.dumps(existing_map))

    mock_blob = MagicMock()

    def make_dl_client(file_path: Path) -> MagicMock:
        client = MagicMock()
        stream = MagicMock()
        stream.readall.return_value = file_path.read_bytes()
        client.download_blob.return_value = stream
        return client

    mock_blob.get_blob_client.side_effect = lambda container, blob: {
        ("test-container", "faiss.index"): make_dl_client(index_path),
        ("test-container", "index_map.json"): make_dl_client(map_path),
    }[container, blob]

    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.7] * dim)]
    )

    result = add_document_to_index(
        document_content="# Doc 6",
        document_path="kb/doc6.md",
        openai_client=mock_openai,
        blob_client=mock_blob,
        container_name="test-container",
        next_id=6,
    )

    assert result["faiss_id"] == 6
    idx_map: dict[str, str] = result["index_map"]  # type: ignore[assignment]
    assert idx_map["6"] == "kb/doc6.md"
    assert idx_map["0"] == "kb/doc0.md"
    assert idx_map["5"] == "kb/doc5.md"
