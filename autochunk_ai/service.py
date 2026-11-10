"""Service-layer facade for AutoChunk AI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

try:
    from .knowledge_base import KnowledgeBase
except ImportError:  # pragma: no cover
    from knowledge_base import KnowledgeBase

try:
    from .ingestion import ingest_document as ingest_document_to_kb
except ImportError:  # pragma: no cover
    from ingestion import ingest_document as ingest_document_to_kb

try:
    from utils import choose_chunking_method as _choose_chunking_method
    from utils import chunk_document as _chunk_document
except ImportError:  # pragma: no cover
    from autochunk_ai.utils import choose_chunking_method as _choose_chunking_method
    from autochunk_ai.utils import chunk_document as _chunk_document


logger = logging.getLogger(__name__)


class AutoChunkService:
    """Thin service wrapper around the document-analysis and chunking engine."""

    def __init__(self, kb_path: str | Path | None = None):
        storage_path = Path(kb_path) if kb_path is not None else None
        self.kb_path = storage_path
        self.kb = self._load_kb(storage_path)

    def _load_kb(self, storage_path: Path | None) -> KnowledgeBase:
        if storage_path is None:
            return KnowledgeBase()
        if storage_path.exists():
            return KnowledgeBase.load(storage_path)
        return KnowledgeBase(storage_path=storage_path)

    def analyze_document(
        self,
        path: str | Path,
        *,
        strategy: str = "auto",
        chunk_size: int | None = None,
        overlap: int | None = None,
        min_chunk_size: int | None = None,
        max_chunk_size: int | None = None,
        preserve_headings: bool | None = None,
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        payload = _choose_chunking_method(str(path), max_pages=max_pages or 30)
        recommendation = payload.get("chunking_method", strategy)
        if strategy and strategy.lower() != "auto":
            recommendation = strategy.lower()

        chunk_args = {
            "strategy": recommendation,
            "chunk_size": chunk_size or 500,
            "overlap": overlap if overlap is not None else 50,
            "min_chunk_size": min_chunk_size or 100,
            "max_chunk_size": max_chunk_size or 800,
            "preserve_headings": preserve_headings if preserve_headings is not None else True,
            "max_pages": max_pages or 30,
        }
        chunking_error = None
        try:
            chunks = _chunk_document(str(path), **chunk_args)
        except Exception as exc:
            # Keep analysis results available, but make failure visible to callers;
            # log the traceback for diagnosis without exposing internals in the response.
            logger.exception("Chunk generation failed during document analysis")
            chunks = []
            chunking_error = {
                "code": "chunking_failed",
                "message": "Chunk generation failed; see server logs for details.",
            }

        return {
            "path": str(path),
            "strategy": recommendation,
            "analysis": payload,
            "chunk_count": len(chunks),
            "chunks": [
                {
                    "chunk_index": chunk.chunk_index,
                    "strategy": chunk.strategy,
                    "token_count": getattr(chunk, "token_count", 0),
                    "start_page": getattr(chunk, "start_page", 1),
                    "end_page": getattr(chunk, "end_page", 1),
                    "text": chunk.text,
                    "metadata": getattr(chunk, "metadata", {}),
                }
                for chunk in chunks
            ],
            "chunking_error": chunking_error,
        }

    def choose_chunking_method(self, path: str | Path, *, max_pages: int | None = None) -> dict[str, Any]:
        return _choose_chunking_method(str(path), max_pages=max_pages or 30)

    def chunk_document(
        self,
        path: str | Path,
        *,
        strategy: str = "auto",
        chunk_size: int | None = None,
        overlap: int | None = None,
        min_chunk_size: int | None = None,
        max_chunk_size: int | None = None,
        preserve_headings: bool | None = None,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        chunk_args = {
            "strategy": strategy,
            "chunk_size": chunk_size or 500,
            "overlap": overlap if overlap is not None else 50,
            "min_chunk_size": min_chunk_size or 100,
            "max_chunk_size": max_chunk_size or 800,
            "preserve_headings": preserve_headings if preserve_headings is not None else True,
            "max_pages": max_pages or 30,
        }
        chunks = _chunk_document(str(path), **chunk_args)
        return [
            {
                "chunk_index": chunk.chunk_index,
                "strategy": chunk.strategy,
                "token_count": getattr(chunk, "token_count", 0),
                "start_page": getattr(chunk, "start_page", 1),
                "end_page": getattr(chunk, "end_page", 1),
                "text": chunk.text,
                "metadata": getattr(chunk, "metadata", {}),
            }
            for chunk in chunks
        ]

    def batch_analyze(
        self,
        paths: Iterable[str | Path],
        *,
        strategy: str = "auto",
        chunk_size: int | None = None,
        overlap: int | None = None,
        min_chunk_size: int | None = None,
        max_chunk_size: int | None = None,
        preserve_headings: bool | None = None,
        max_pages: int | None = None,
    ) -> dict[str, Any]:
        result_paths = list(paths)
        results = [
            self.analyze_document(
                item,
                strategy=strategy,
                chunk_size=chunk_size,
                overlap=overlap,
                min_chunk_size=min_chunk_size,
                max_chunk_size=max_chunk_size,
                preserve_headings=preserve_headings,
                max_pages=max_pages,
            )
            for item in result_paths
        ]
        return {
            "count": len(results),
            "results": results,
        }

    def ingest_document(
        self,
        path: str | Path,
        *,
        storage_path: str | Path | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        target_kb = self.kb if storage_path is None else KnowledgeBase.load(storage_path) if Path(storage_path).exists() else KnowledgeBase(storage_path=storage_path)
        ingested = target_kb.ingest_document(path, **kwargs)
        if storage_path is not None:
            target_kb.save(storage_path)
        else:
            self.kb = target_kb
        return {
            "source_path": str(path),
            "ingested_count": len(ingested),
            "entries": [entry.to_dict() for entry in ingested],
        }


__all__ = ["AutoChunkService"]
