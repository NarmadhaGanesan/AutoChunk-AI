from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from utils import choose_chunking_method, chunk_document
except Exception:  # pragma: no cover - fallback for alternate layouts
    choose_chunking_method = None
    chunk_document = None


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".jpg", ".jpeg", ".png"}


@dataclass
class BatchReport:
    """Container for a batch document-processing run."""

    folder: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    documents: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_documents(self) -> int:
        return len(self.documents)

    @property
    def processed_documents(self) -> int:
        return sum(1 for item in self.documents if item.get("status") == "processed")

    @property
    def failed_documents(self) -> int:
        return sum(1 for item in self.documents if item.get("status") == "failed")

    @property
    def skipped_documents(self) -> int:
        return sum(1 for item in self.documents if item.get("status") == "skipped")

    def add_document(self, path: str, *, status: str, recommendation: dict[str, Any] | None = None, chunks: list[dict[str, Any]] | None = None, error: str | None = None) -> None:
        payload: dict[str, Any] = {
            "path": path,
            "status": status,
        }
        if recommendation is not None:
            payload["recommendation"] = recommendation
        if chunks is not None:
            payload["chunks"] = chunks
        if error is not None:
            payload["error"] = error
        self.documents.append(payload)

    def to_dict(self) -> dict[str, Any]:
        return {
            "folder": self.folder,
            "generated_at": self.generated_at,
            "total_documents": self.total_documents,
            "processed_documents": self.processed_documents,
            "failed_documents": self.failed_documents,
            "skipped_documents": self.skipped_documents,
            "documents": self.documents,
        }


def _iter_document_files(folder: str | Path, recursive: bool = True) -> Iterable[Path]:
    root = Path(folder)
    if not root.exists():
        return []
    if recursive:
        iterator = root.rglob("*")
    else:
        iterator = root.iterdir()
    matched = []
    for candidate in iterator:
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            matched.append(candidate)
    return sorted(matched, key=lambda p: str(p).lower())


def _load_recommendation(path: str | Path, *, strategy: str = "auto", max_pages: int = 30) -> dict[str, Any]:
    if choose_chunking_method is None:
        return {
            "chunking_method": "recursive",
            "reason": "No chunking implementation available in the current environment; used recursive fallback.",
        }
    try:
        return choose_chunking_method(str(path), max_pages=max_pages)
    except Exception as exc:  # pragma: no cover - safety fallback
        return {
            "chunking_method": "recursive",
            "reason": f"Recommendation failed ({type(exc).__name__}: {exc}; used recursive fallback.",
        }


def _generate_chunks(path: str | Path, *, strategy: str = "auto", chunk_size: int = 500, overlap: int = 50, min_chunk_size: int = 100, max_chunk_size: int = 800, preserve_headings: bool = True, max_pages: int = 30) -> list[dict[str, Any]]:
    if chunk_document is None:
        return []
    try:
        chunks = chunk_document(
            str(path),
            strategy=strategy,
            chunk_size=chunk_size,
            overlap=overlap,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            preserve_headings=preserve_headings,
            max_pages=max_pages,
        )
        return [
            {
                "chunk_index": chunk.chunk_index,
                "strategy": chunk.strategy,
                "token_count": chunk.token_count,
                "start_page": chunk.start_page,
                "end_page": chunk.end_page,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ]
    except Exception:
        return []


def process_document_folder(
    folder_path: str | Path,
    *,
    recursive: bool = True,
    strategy: str = "auto",
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 100,
    max_chunk_size: int = 800,
    preserve_headings: bool = True,
    max_pages: int = 30,
) -> BatchReport:
    """Process every supported document in a folder and produce a batch report."""

    folder = Path(folder_path)
    report = BatchReport(folder=str(folder))

    if not folder.exists():
        report.add_document(str(folder), status="failed", error="Folder does not exist.")
        return report

    for file_path in _iter_document_files(folder, recursive=recursive):
        path_str = str(file_path)
        try:
            recommendation = _load_recommendation(file_path, strategy=strategy, max_pages=max_pages)
            chunks = _generate_chunks(
                file_path,
                strategy=recommendation.get("chunking_method", strategy),
                chunk_size=chunk_size,
                overlap=overlap,
                min_chunk_size=min_chunk_size,
                max_chunk_size=max_chunk_size,
                preserve_headings=preserve_headings,
                max_pages=max_pages,
            )
            report.add_document(path_str, status="processed", recommendation=recommendation, chunks=chunks)
        except Exception as exc:  # pragma: no cover - guard against unexpected file issues
            report.add_document(path_str, status="failed", error=str(exc))

    if not report.documents:
        report.add_document(str(folder), status="skipped", error="No supported documents found in the folder.")

    return report


def generate_batch_report(
    folder_path: str | Path,
    *,
    recursive: bool = True,
    strategy: str = "auto",
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 100,
    max_chunk_size: int = 800,
    preserve_headings: bool = True,
    max_pages: int = 30,
) -> BatchReport:
    """Alias for process_document_folder used by callers expecting a report factory."""

    return process_document_folder(
        folder_path,
        recursive=recursive,
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
        preserve_headings=preserve_headings,
        max_pages=max_pages,
    )


def summarize_batch_report(report: BatchReport | dict[str, Any]) -> dict[str, Any]:
    """Summarize a batch report into a compact breakdown by recommendation."""

    if isinstance(report, dict):
        docs = report.get("documents", [])
    else:
        docs = report.documents

    counts = {"processed": 0, "failed": 0, "skipped": 0}
    by_method: dict[str, int] = {}
    total_chunks = 0

    for item in docs:
        status = item.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

        recommendation = item.get("recommendation") or {}
        method = recommendation.get("chunking_method", "unknown")
        by_method[method] = by_method.get(method, 0) + 1

        for chunk in item.get("chunks", []) or []:
            total_chunks += 1

    summary = {
        "total_documents": len(docs),
        "processed": counts.get("processed", 0),
        "failed": counts.get("failed", 0),
        "skipped": counts.get("skipped", 0),
        "total_chunks": total_chunks,
        "chunking_methods": by_method,
    }
    return summary


__all__ = [
    "BatchReport",
    "generate_batch_report",
    "process_document_folder",
    "summarize_batch_report",
]
