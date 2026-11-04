"""Public channel for chunk generation helpers."""

from utils import chunk_document


def chunk_document_json(path, **kwargs):
    chunks = chunk_document(path, **kwargs)
    return [
        {
            "chunk_index": chunk.chunk_index,
            "strategy": chunk.strategy,
            "token_count": getattr(chunk, "token_count", 0),
            "text": chunk.text,
            "start_page": getattr(chunk, "start_page", 1),
            "end_page": getattr(chunk, "end_page", 1),
            "metadata": getattr(chunk, "metadata", {}),
        }
        for chunk in chunks
    ]


__all__ = ["chunk_document", "chunk_document_json"]
