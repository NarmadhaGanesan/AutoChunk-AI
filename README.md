# AutoChunk-AI

**Choose the right chunking strategy for every document.** AutoChunk-AI analyzes document structure and recommends either hierarchical or recursive chunking. When the structure is ambiguous, it can use an AI-assisted fallback.

Designed for document-aware retrieval and chunk generation, AutoChunk-AI supports PDFs, DOCX files, Markdown, plain text, and OCR from scanned images.

## Contents

- [Features](#features)
- [Supported file types](#supported-file-types)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Python usage](#python-usage)
- [API usage](#api-usage)
- [Error handling](#error-handling)
- [Project structure](#project-structure)
- [License](#license)

## Features

- Analyzes headings, numbering, bookmarks, and formatting cues to detect document structure.
- Recommends `hierarchical` or `recursive` chunking.
- Generates chunks while preserving heading context.
- Supports common document, text, and image formats.
- Provides a FastAPI service for document analysis and upload processing.
- Includes tests for core chunking behavior and API endpoints.

## Supported file types

| Category | Formats |
| --- | --- |
| Documents | PDF, DOCX |
| Text and data | Markdown (`.md`), plain text (`.txt`), CSV, JSON, HTML, XML, YAML, RTF, LOG |
| Images (OCR) | `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.gif` |

## Installation

Install the project dependencies:

```bash
pip install -r requirements.txt
```

Or install the project in editable mode:

```bash
pip install -e .
```

## Quick start

See the available command-line options:

```bash
python -m autochunk_ai --help
```

Get a chunking recommendation for a document:

```bash
python -m autochunk_ai sample.pdf
```

Generate chunks using automatic strategy selection:

```bash
python -m autochunk_ai sample.md --strategy auto --chunk
```

## Python usage

```python
from utils import choose_chunking_method, chunk_document

recommendation = choose_chunking_method("sample.pdf")
print(recommendation)

chunks = chunk_document(
    "sample.md",
    strategy="hierarchical",
    chunk_size=500,
    overlap=50,
)
print(len(chunks))
```

## API usage

Start the FastAPI application with Uvicorn:

```bash
uvicorn autochunk_ai.api:app --reload
```

The upload-based analysis endpoint is:

```text
POST /api/analyze
```

Available analysis fields include:

| Field | Description |
| --- | --- |
| `strategy` | `auto`, `hierarchical`, or `recursive` |
| `chunk_size` | Desired chunk size |
| `overlap` | Overlap between chunks |
| `min_chunk_size` | Minimum chunk size |
| `max_chunk_size` | Maximum chunk size |
| `max_pages` | Maximum pages to process |
| `preserve_headings` | Whether to preserve heading context |

## Error handling

AutoChunk-AI handles document processing and chunk-generation failures explicitly:

- Unsupported or unreadable files receive clear validation messages.
- Chunk-generation failures are logged on the server.
- If chunking cannot complete, API responses include a structured `chunking_error` payload.
- Internal exception details are not exposed in client-facing responses.

## Project structure

```text
.
├── autochunk_ai/
│   ├── __init__.py
│   ├── __main__.py
│   ├── api.py
│   ├── chunking.py
│   ├── ingestion.py
│   ├── knowledge_base.py
│   ├── retrieval.py
│   ├── scoring.py
│   └── service.py
├── constants.py
├── models.py
├── utils.py
├── tests/
│   ├── test_api.py
│   └── test_core.py
├── web/
├── frontend/
├── requirements.txt
├── pyproject.toml
├── UI_SETUP.md
└── README.md
```

## License

This project is intended for research and experimentation in document-aware AI retrieval workflows.
