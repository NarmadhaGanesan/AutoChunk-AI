from __future__ import annotations

import csv
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from utils import choose_chunking_method, chunk_document
except Exception:  # pragma: no cover - fallback for alternate layouts
    choose_chunking_method = None
    chunk_document = None


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".md",
    ".txt",
    ".csv",
    ".json",
    ".html",
    ".htm",
    ".xml",
    ".rtf",
    ".log",
    ".yaml",
    ".yml",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
    ".gif",
}
OCR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}


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

    def add_document(
        self,
        path: str,
        *,
        status: str,
        recommendation: dict[str, Any] | None = None,
        chunks: list[dict[str, Any]] | None = None,
        error: str | None = None,
        file_type: str | None = None,
        retries: int = 0,
        warnings: list[str] | None = None,
        page_count: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "path": path,
            "status": status,
            "file_type": file_type or Path(path).suffix.lower() or "unknown",
            "retry_count": retries,
        }
        if page_count is not None:
            payload["page_count"] = page_count
        if recommendation is not None:
            payload["recommendation"] = recommendation
        if chunks is not None:
            payload["chunks"] = chunks
        if error is not None:
            payload["error"] = error
        if warnings:
            payload["warnings"] = warnings
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

    def summary(self) -> dict[str, Any]:
        return summarize_batch_report(self)

    def export(self, output_path: str | Path | None = None, fmt: str = "json", **kwargs) -> str | dict[str, Any]:
        return export_batch_report(self, output_path=output_path, fmt=fmt, **kwargs)


def _iter_document_files(folder: str | Path, recursive: bool = True) -> Iterable[Path]:
    root = Path(folder)
    if not root.exists() or not root.is_dir():
        return []

    iterator = root.rglob("*") if recursive else root.iterdir()
    matched: list[Path] = []
    for candidate in iterator:
        if not candidate.is_file():
            continue
        if candidate.name.startswith("."):
            continue
        if candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            matched.append(candidate)
    return sorted(matched, key=lambda p: str(p).lower())


def _detect_file_type(path: str | Path) -> str:
    return Path(path).suffix.lower() or "unknown"


def _is_ocr_document(path: str | Path) -> bool:
    return _detect_file_type(path) in OCR_EXTENSIONS


def _load_recommendation(path: str | Path, *, strategy: str = "auto", max_pages: int = 30) -> dict[str, Any]:
    if choose_chunking_method is None:
        return {
            "chunking_method": "recursive",
            "reason": "No chunking implementation available in the current environment; used recursive fallback.",
            "confidence": 0.0,
        }
    try:
        recommendation = choose_chunking_method(str(path), max_pages=max_pages)
        if not isinstance(recommendation, dict):
            raise TypeError("Recommendation result must be a dict.")
        recommendation.setdefault("chunking_method", "recursive")
        recommendation.setdefault("reason", "No reason supplied.")
        recommendation.setdefault("confidence", 0.0)
        if recommendation.get("chunking_method") not in {"hierarchical", "recursive"}:
            recommendation["chunking_method"] = "recursive"
        return recommendation
    except Exception as exc:  # pragma: no cover - safety fallback
        return {
            "chunking_method": "recursive",
            "reason": f"Recommendation failed ({type(exc).__name__}: {exc}; used recursive fallback.",
            "confidence": 0.0,
        }


def _generate_chunks(
    path: str | Path,
    *,
    strategy: str = "auto",
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 100,
    max_chunk_size: int = 800,
    preserve_headings: bool = True,
    max_pages: int = 30,
) -> list[dict[str, Any]]:
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


def _process_single_document(
    file_path: str | Path,
    *,
    strategy: str = "auto",
    chunk_size: int = 500,
    overlap: int = 50,
    min_chunk_size: int = 100,
    max_chunk_size: int = 800,
    preserve_headings: bool = True,
    max_pages: int = 30,
    retries: int = 0,
    backoff_seconds: float = 0.25,
) -> dict[str, Any]:
    path_str = str(file_path)
    file_type = _detect_file_type(path_str)
    last_error: str | None = None
    warning_messages: list[str] = []
    attempts = max(1, retries + 1)

    for attempt in range(1, attempts + 1):
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
            if _is_ocr_document(path_str):
                warning_messages.append("OCR-capable image/scanned document detected; processed with image/OCR-aware path.")
            return {
                "path": path_str,
                "status": "processed",
                "file_type": file_type,
                "retry_count": max(0, attempt - 1),
                "ocr_detected": _is_ocr_document(path_str),
                "recommendation": recommendation,
                "chunks": chunks,
                "warnings": warning_messages,
            }
        except Exception as exc:  # pragma: no cover - safety fallback
            last_error = str(exc)
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)
                continue
            return {
                "path": path_str,
                "status": "failed",
                "file_type": file_type,
                "retry_count": max(0, attempt - 1),
                "ocr_detected": _is_ocr_document(path_str),
                "error": last_error,
                "warnings": warning_messages,
            }

    return {
        "path": path_str,
        "status": "failed",
        "file_type": file_type,
        "retry_count": retries,
        "ocr_detected": _is_ocr_document(path_str),
        "error": last_error or "Unknown processing failure",
        "warnings": warning_messages,
    }


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
    retries: int = 2,
    backoff_seconds: float = 0.25,
) -> BatchReport:
    """Process every supported document in a folder and produce a batch report."""

    folder = Path(folder_path)
    report = BatchReport(folder=str(folder))

    if not folder.exists():
        report.add_document(str(folder), status="failed", error="Folder does not exist.", file_type="folder")
        return report

    documents = list(_iter_document_files(folder, recursive=recursive))
    if not documents:
        report.add_document(str(folder), status="skipped", error="No supported documents found in the folder.", file_type="folder")
        return report

    for file_path in documents:
        payload = _process_single_document(
            file_path,
            strategy=strategy,
            chunk_size=chunk_size,
            overlap=overlap,
            min_chunk_size=min_chunk_size,
            max_chunk_size=max_chunk_size,
            preserve_headings=preserve_headings,
            max_pages=max_pages,
            retries=retries,
            backoff_seconds=backoff_seconds,
        )
        report.documents.append(payload)

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
    retries: int = 2,
    backoff_seconds: float = 0.25,
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
        retries=retries,
        backoff_seconds=backoff_seconds,
    )


def summarize_batch_report(report: BatchReport | dict[str, Any]) -> dict[str, Any]:
    """Summarize a batch report into a compact breakdown by recommendation and file type."""

    if isinstance(report, dict):
        docs = report.get("documents", [])
    else:
        docs = report.documents

    counts = {"processed": 0, "failed": 0, "skipped": 0}
    by_method: dict[str, int] = {}
    by_file_type: dict[str, int] = {}
    total_chunks = 0
    total_tokens = 0

    for item in docs:
        status = item.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

        recommendation = item.get("recommendation") or {}
        method = recommendation.get("chunking_method", "unknown")
        by_method[method] = by_method.get(method, 0) + 1

        file_type = item.get("file_type") or _detect_file_type(item.get("path", ""))
        by_file_type[file_type] = by_file_type.get(file_type, 0) + 1

        for chunk in item.get("chunks", []) or []:
            total_chunks += 1
            total_tokens += int(chunk.get("token_count") or 0)

    summary = {
        "total_documents": len(docs),
        "processed": counts.get("processed", 0),
        "failed": counts.get("failed", 0),
        "skipped": counts.get("skipped", 0),
        "total_chunks": total_chunks,
        "total_tokens": total_tokens,
        "chunking_methods": by_method,
        "file_types": by_file_type,
    }
    if summary["total_documents"]:
        summary["success_rate"] = round(summary["processed"] / summary["total_documents"], 4)
    else:
        summary["success_rate"] = 0.0
    return summary


def export_batch_report(
    report: BatchReport | dict[str, Any],
    *,
    output_path: str | Path | None = None,
    fmt: str = "json",
    include_summary: bool = True,
) -> str | dict[str, Any]:
    """Export a report to JSON or CSV format."""

    payload = report.to_dict() if isinstance(report, BatchReport) else report
    if include_summary:
        summary = summarize_batch_report(payload)
        payload = {**payload, "summary": summary}

    fmt = (fmt or "json").lower()
    if fmt == "json":
        content = json.dumps(payload, indent=2, ensure_ascii=False)
        if output_path:
            Path(output_path).write_text(content, encoding="utf-8")
            return str(output_path)
        return content

    if fmt == "csv":
        rows = []
        for item in payload.get("documents", []):
            rows.append(
                {
                    "path": item.get("path", ""),
                    "status": item.get("status", "unknown"),
                    "file_type": item.get("file_type", "unknown"),
                    "retry_count": item.get("retry_count", 0),
                    "chunk_count": len(item.get("chunks", []) or []),
                    "chunking_method": (item.get("recommendation") or {}).get("chunking_method", "unknown"),
                    "error": item.get("error", ""),
                }
            )
        output = []
        fieldnames = ["path", "status", "file_type", "retry_count", "chunk_count", "chunking_method", "error"]
        for row in rows:
            output.append({key: row.get(key, "") for key in fieldnames})

        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with output_file.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(output)
            return str(output_file)

        buffer = []
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)
        return "\n".join(buffer)

    raise ValueError("Unsupported export format. Use 'json' or 'csv'.")


def save_batch_report(
    report: BatchReport | dict[str, Any],
    output_path: str | Path,
    *,
    fmt: str = "json",
    include_summary: bool = True,
) -> str:
    """Persist a batch report to disk."""
    return str(export_batch_report(report, output_path=output_path, fmt=fmt, include_summary=include_summary))


__all__ = [
    "BatchReport",
    "generate_batch_report",
    "process_document_folder",
    "summarize_batch_report",
    "export_batch_report",
    "save_batch_report",
]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch process a folder of documents with chunk recommendation and reporting.")
    parser.add_argument("folder", help="Folder to process")
    parser.add_argument("--recursive", action="store_true", default=True, help="Recursively process nested directories")
    parser.add_argument("--non-recursive", dest="recursive", action="store_false", help="Only process the top level")
    parser.add_argument("--strategy", choices=["auto", "hierarchical", "recursive"], default="auto")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--min-chunk-size", type=int, default=100)
    parser.add_argument("--max-chunk-size", type=int, default=800)
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--backoff-seconds", type=float, default=0.25)
    parser.add_argument("--export", help="Optional path to export the batch report JSON or CSV")
    parser.add_argument("--export-format", choices=["json", "csv"], default="json")
    args = parser.parse_args()

    report = process_document_folder(
        args.folder,
        recursive=args.recursive,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        min_chunk_size=args.min_chunk_size,
        max_chunk_size=args.max_chunk_size,
        max_pages=args.max_pages,
        retries=args.retries,
        backoff_seconds=args.backoff_seconds,
    )
    print(json.dumps(summarize_batch_report(report), indent=2))
    if args.export:
        export_batch_report(report, output_path=args.export, fmt=args.export_format)
        print(f"Batch report exported to {args.export}")
