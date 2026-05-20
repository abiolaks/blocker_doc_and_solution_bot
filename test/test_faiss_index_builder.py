"""Tests for FAISS index builder module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np


def test_collect_documents_finds_md_files(tmp_path: Path) -> None:
    """collect_documents should find all .md files under a knowledge base directory."""
    from blocker_doc_and_solution_bot.index_builder.build import collect_documents

    # Arrange: create a fake KB with two projects
    project_a = tmp_path / "project-alpha"
    project_a.mkdir(parents=True)
    (project_a / "2026-05-01-error-1.md").write_text("# Error 1\n\n## Problem\n...")
    (project_a / "2026-05-02-error-2.md").write_text("# Error 2\n\n## Problem\n...")

    project_b = tmp_path / "project-beta"
    project_b.mkdir(parents=True)
    (project_b / "2026-05-03-issue.md").write_text("# Issue\n\n## Problem\n...")

    # Add a non-markdown file that should be ignored
    (tmp_path / "readme.txt").write_text("not a doc")

    # Act
    docs = collect_documents(tmp_path)

    # Assert
    assert len(docs) == 3
    paths = {d["path"] for d in docs}
    assert str(project_a / "2026-05-01-error-1.md") in paths
    assert str(project_a / "2026-05-02-error-2.md") in paths
    assert str(project_b / "2026-05-03-issue.md") in paths

    # Verify content is read correctly
    doc = next(d for d in docs if "error-1" in d["path"])
    assert doc["content"] == "# Error 1\n\n## Problem\n..."


def test_collect_documents_empty_dir(tmp_path: Path) -> None:
    """collect_documents should return an empty list for empty directories."""
    from blocker_doc_and_solution_bot.index_builder.build import collect_documents

    docs = collect_documents(tmp_path)
    assert docs == []


def test_collect_documents_skips_directories_with_md_suffix(tmp_path: Path) -> None:
    """collect_documents should skip directories whose names end in .md."""
    from blocker_doc_and_solution_bot.index_builder.build import collect_documents

    (tmp_path / "Agentic_RAG_system.md").mkdir()
    (tmp_path / "Agentic_RAG_system.md" / "doc.md").write_text("# Nested doc")
    (tmp_path / "real-file.md").write_text("# Real file")

    docs = collect_documents(tmp_path)

    # Only real .md files collected, not the directory itself.
    # The nested doc.md inside the directory IS a file and should be counted.
    assert len(docs) == 2


def test_embed_documents_returns_numpy_array() -> None:
    """embed_documents should return a 2D numpy array with one row per document."""
    from blocker_doc_and_solution_bot.index_builder.build import embed_documents

    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
            MagicMock(embedding=[0.3] * 1536),
        ]
    )

    docs = [
        {"path": "/kb/doc1.md", "content": "doc one"},
        {"path": "/kb/doc2.md", "content": "doc two"},
        {"path": "/kb/doc3.md", "content": "doc three"},
    ]

    result = embed_documents(docs, mock_client)

    assert isinstance(result, np.ndarray)
    assert result.shape == (3, 1536)


def test_embed_documents_empty_input() -> None:
    """embed_documents should return an empty array for empty input."""
    from blocker_doc_and_solution_bot.index_builder.build import embed_documents

    mock_client = MagicMock()
    result = embed_documents([], mock_client)

    assert isinstance(result, np.ndarray)
    assert result.shape == (0, 1536)
    mock_client.embeddings.create.assert_not_called()


def test_build_index_creates_faiss_index(tmp_path: Path) -> None:
    """build_index should create a FAISS index file from embeddings."""
    from blocker_doc_and_solution_bot.index_builder.build import build_index

    embeddings = np.random.rand(5, 1536).astype(np.float32)
    output_path = tmp_path / "faiss.index"

    index = build_index(embeddings, output_path)

    assert index is not None
    assert output_path.exists()
    assert index.ntotal == 5


def test_build_index_handles_empty_embeddings(tmp_path: Path) -> None:
    """build_index should return None for empty embeddings array."""
    from blocker_doc_and_solution_bot.index_builder.build import build_index

    embeddings = np.array([], dtype=np.float32).reshape(0, 1536)
    output_path = tmp_path / "faiss.index"

    index = build_index(embeddings, output_path)

    assert index is None
    assert not output_path.exists()


def test_create_index_map_maps_ids_to_paths() -> None:
    """create_index_map should map integer IDs to file paths."""
    from blocker_doc_and_solution_bot.index_builder.build import create_index_map

    docs = [
        {"path": "/kb/project-a/doc1.md", "content": "a"},
        {"path": "/kb/project-b/doc2.md", "content": "b"},
    ]

    index_map = create_index_map(docs)

    assert index_map == {
        "0": "/kb/project-a/doc1.md",
        "1": "/kb/project-b/doc2.md",
    }


def test_upload_to_blob_calls_upload_blob(tmp_path: Path) -> None:
    """upload_to_blob should upload index and map files to blob storage."""
    from blocker_doc_and_solution_bot.index_builder.build import upload_to_blob

    mock_client = MagicMock()
    index_path = tmp_path / "faiss.index"
    map_path = tmp_path / "index_map.json"
    index_path.write_bytes(b"fake-index-data")
    map_path.write_text('{"0": "path/doc.md"}')

    upload_to_blob(mock_client, index_path, map_path, "test-container")

    assert mock_client.get_blob_client.call_count == 2
    mock_client.get_blob_client.assert_any_call(container="test-container", blob="faiss.index")
    mock_client.get_blob_client.assert_any_call(container="test-container", blob="index_map.json")


def test_rebuild_index_end_to_end(tmp_path: Path) -> None:
    """rebuild_index should collect, embed, build, map, and upload end-to-end."""
    from blocker_doc_and_solution_bot.index_builder.build import rebuild_index

    # Arrange: create a fake KB with two docs
    (tmp_path / "project-a").mkdir()
    (tmp_path / "project-a" / "doc1.md").write_text("# Doc 1\n\nContent A")
    (tmp_path / "project-b").mkdir()
    (tmp_path / "project-b" / "doc2.md").write_text("# Doc 2\n\nContent B")

    mock_openai = MagicMock()
    mock_openai.embeddings.create.return_value = MagicMock(
        data=[
            MagicMock(embedding=[0.1] * 1536),
            MagicMock(embedding=[0.2] * 1536),
        ]
    )

    mock_blob = MagicMock()

    # Act
    index = rebuild_index(
        kb_dir=tmp_path,
        openai_client=mock_openai,
        blob_client=mock_blob,
        container_name="test-container",
        index_path=tmp_path / "faiss.index",
        map_path=tmp_path / "index_map.json",
    )

    # Assert
    assert index is not None
    assert index.ntotal == 2

    # Verify uploads happened
    assert mock_blob.get_blob_client.call_count == 2

    # Verify index_map.json was written with correct mappings
    import json

    map_data = json.loads((tmp_path / "index_map.json").read_text())
    assert len(map_data) == 2
    assert all(str(i) in map_data for i in range(2))
