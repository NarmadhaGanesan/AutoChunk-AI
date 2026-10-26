"""Batch document processing utilities for AutoChunk-AI."""

from .processor import (
    BatchReport,
    generate_batch_report,
    process_document_folder,
    summarize_batch_report,
)

__all__ = [
    "BatchReport",
    "generate_batch_report",
    "process_document_folder",
    "summarize_batch_report",
]
