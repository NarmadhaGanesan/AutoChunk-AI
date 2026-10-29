"""Retrieval helpers for the AutoChunk AI knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .knowledge_base import KnowledgeBase


def retrieve(query: str, *, kb: KnowledgeBase | None = None, top_k: int = 5, min_score: float = 0.0, storage_path: str | Path | None = None) -> list[dict[str, Any]]:
    if kb is None:
        kb = KnowledgeBase.load(storage_path) if storage_path else KnowledgeBase()
    return kb.search(query, top_k=top_k, min_score=min_score)


__all__ = ["retrieve"]
