"""Compatibility wrapper for the ingestion helper."""

from ingestion import KnowledgeBase


def ingest_document(path, *, kb: KnowledgeBase | None = None, **kwargs):
    base = kb or KnowledgeBase()
    base.ingest_document(path, **kwargs)
    return base


def ingest_folder(folder_path, *, kb: KnowledgeBase | None = None, **kwargs):
    base = kb or KnowledgeBase()
    base.ingest_folder(folder_path, **kwargs)
    return base


__all__ = ["ingest_document", "ingest_folder"]
