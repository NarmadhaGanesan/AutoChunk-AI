"""Compatibility wrapper for the retrieval helper."""

from ingestion import KnowledgeBase


def retrieve(query: str, *, kb: KnowledgeBase | None = None, top_k: int = 5, min_score: float = 0.0):
    base = kb or KnowledgeBase()
    return base.search(query, top_k=top_k, min_score=min_score)


__all__ = ["retrieve"]
