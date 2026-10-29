"""Helpers for ingesting document chunks into a local knowledge base."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .knowledge_base import KnowledgeBase


def ingest_document(path: str | Path, *, kb: KnowledgeBase | None = None, **kwargs: Any) -> KnowledgeBase:
    base = kb or KnowledgeBase()
    base.ingest_document(path, **kwargs)
    return base


def ingest_folder(folder_path: str | Path, *, kb: KnowledgeBase | None = None, **kwargs: Any) -> KnowledgeBase:
    base = kb or KnowledgeBase()
    base.ingest_folder(folder_path, **kwargs)
    return base


__all__ = ["ingest_document", "ingest_folder"]
