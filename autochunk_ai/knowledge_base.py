"""AutoChunk AI package exports."""

from .chunking import chunk_document
from .ingestion import ingest_document, ingest_folder
from .knowledge_base import KnowledgeBase, KnowledgeEntry
from .retrieval import retrieve
from .scoring import choose_chunking_method

__all__ = [
    "KnowledgeBase",
    "KnowledgeEntry",
    "chunk_document",
    "choose_chunking_method",
    "ingest_document",
    "ingest_folder",
    "retrieve",
]
