"""Batch document processing utilities for AutoChunk-AI."""

from .processor import (
    BatchReport,
    export_batch_report,
    generate_batch_report,
    process_document_folder,
    save_batch_report,
    summarize_batch_report,
)

__all__ = [
    "BatchReport",
    "generate_batch_report",
    "process_document_folder",
    "summarize_batch_report",
    "export_batch_report",
    "save_batch_report",
]
