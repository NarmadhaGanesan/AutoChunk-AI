"""FastAPI service exposing the AutoChunk document-analysis engine."""

from __future__ import annotations

from typing import Any, Sequence

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .service import AutoChunkService

service = AutoChunkService()
app = FastAPI(
    title="AutoChunk AI Service",
    description="REST API for document analysis and chunking recommendations.",
    version="1.0.0",
)


class DocumentRequest(BaseModel):
    path: str = Field(..., description="Path to the document to analyze")
    strategy: str = Field("auto", description="Chunking strategy: auto, hierarchical, or recursive")
    chunk_size: int | None = Field(None, ge=1)
    overlap: int | None = Field(None, ge=0)
    min_chunk_size: int | None = Field(None, ge=1)
    max_chunk_size: int | None = Field(None, ge=1)
    preserve_headings: bool | None = None
    max_pages: int | None = Field(None, ge=1)


class BatchAnalyzeRequest(DocumentRequest):
    paths: Sequence[str] | None = Field(default=None, description="Optional list of file paths to batch analyze")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-document")
def analyze_document(payload: DocumentRequest) -> dict[str, Any]:
    return service.analyze_document(
        payload.path,
        strategy=payload.strategy,
        chunk_size=payload.chunk_size,
        overlap=payload.overlap,
        min_chunk_size=payload.min_chunk_size,
        max_chunk_size=payload.max_chunk_size,
        preserve_headings=payload.preserve_headings,
        max_pages=payload.max_pages,
    )


@app.post("/choose-chunking-method")
def choose_chunking_method(payload: DocumentRequest) -> dict[str, Any]:
    return service.choose_chunking_method(payload.path, max_pages=payload.max_pages)


@app.post("/chunk-document")
def chunk_document(payload: DocumentRequest) -> list[dict[str, Any]]:
    return service.chunk_document(
        payload.path,
        strategy=payload.strategy,
        chunk_size=payload.chunk_size,
        overlap=payload.overlap,
        min_chunk_size=payload.min_chunk_size,
        max_chunk_size=payload.max_chunk_size,
        preserve_headings=payload.preserve_headings,
        max_pages=payload.max_pages,
    )


@app.post("/batch-analyze")
def batch_analyze(payload: BatchAnalyzeRequest) -> dict[str, Any]:
    paths = payload.paths or [payload.path]
    return service.batch_analyze(
        paths,
        strategy=payload.strategy,
        chunk_size=payload.chunk_size,
        overlap=payload.overlap,
        min_chunk_size=payload.min_chunk_size,
        max_chunk_size=payload.max_chunk_size,
        preserve_headings=payload.preserve_headings,
        max_pages=payload.max_pages,
    )


__all__ = ["app", "service"]
