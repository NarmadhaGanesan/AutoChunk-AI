"""Public API for AutoChunk AI."""

from .ingestion import ingest_document, ingest_folder
from .knowledge_base import KnowledgeBase, KnowledgeEntry
from .retrieval import retrieve
from .scoring import choose_chunking_method
from .chunking import chunk_document

__all__ = [
    "KnowledgeBase",
    "KnowledgeEntry",
    "chunk_document",
    "choose_chunking_method",
    "ingest_document",
    "ingest_folder",
    "retrieve",
]
