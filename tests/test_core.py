"""Tests for the core chunking and knowledge-base behavior."""

from __future__ import annotations

import pytest

from autochunk_ai.ingestion import KnowledgeBase
from constants import HIERARCHICAL, RECURSIVE
from utils import choose_chunking_method, chunk_document


def _write_doc(tmp_path, filename: str, content: str) -> str:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_choose_chunking_method_for_structured_markdown(tmp_path):
    path = _write_doc(
        tmp_path,
        "structured.md",
        "# Overview\n\nThis report explains the process.\n\n## Background\n\nThe team started in 2021.\n\n### Scope\n\nThis is the project scope.\n\n## Results\n\nThe pilot succeeded.",
    )

    result = choose_chunking_method(path)

    assert result["chunking_method"] == HIERARCHICAL
    assert "Rule score" in result["reason"]


def test_choose_chunking_method_for_plain_notes(tmp_path):
    path = _write_doc(
        tmp_path,
        "notes.txt",
        "Alpha beta gamma\nDelta epsilon zeta\nEta theta iota\nKappa lambda mu\nNu xi omicron\n",
    )

    result = choose_chunking_method(path)

    assert result["chunking_method"] == RECURSIVE


def test_chunk_document_generates_chunks_and_preserves_strategy(tmp_path):
    path = _write_doc(
        tmp_path,
        "example.md",
        "# Title\n\nThis is a paragraph about the product.\n\n## Details\n\nMore explanatory text about the launch plan and deliverables.",
    )

    chunks = chunk_document(
        path,
        strategy=HIERARCHICAL,
        chunk_size=20,
        overlap=5,
        min_chunk_size=8,
        max_chunk_size=80,
    )

    assert chunks
    assert all(chunk.strategy == HIERARCHICAL for chunk in chunks)
    assert all(chunk.text.strip() for chunk in chunks)
    assert all(chunk.metadata.get("section_heading") is not None or chunk.metadata.get("fallback") for chunk in chunks)


def test_knowledge_base_search_ranks_relevant_entries():
    kb = KnowledgeBase()
    kb.add_entry({
        "id": "entry-1",
        "source_path": "alpha.txt",
        "text": "alpha beta gamma",
        "metadata": {},
        "chunk_index": 1,
        "strategy": "recursive",
        "token_count": 3,
    })
    kb.add_entry({
        "id": "entry-2",
        "source_path": "beta.txt",
        "text": "omega delta",
        "metadata": {},
        "chunk_index": 1,
        "strategy": "recursive",
        "token_count": 2,
    })

    results = kb.search("alpha", top_k=5)

    assert results
    assert results[0]["id"] == "entry-1"
    assert results[0]["score"] >= 0.0


def test_invalid_strategy_raises_value_error(tmp_path):
    path = _write_doc(tmp_path, "bad.txt", "Some simple text for chunking.")

    with pytest.raises(ValueError):
        chunk_document(path, strategy="not-a-real-strategy")
