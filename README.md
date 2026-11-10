# AutoChunk-AI

AutoChunk-AI automatically decides whether a document is better suited for hierarchical chunking or recursive chunking, with rule-based analysis and an optional AI-backed fallback for ambiguous cases.

It is built for document-structure-aware retrieval and chunk generation across PDFs, DOCX files, Markdown, plain text, and OCR from scanned images.

## Features

- Detects document structure using headings, numbering, bookmarks, and formatting cues
- Recommends either `hierarchical` or `recursive` chunking
- Splits documents into chunks while preserving heading context
- Supports common text and document formats
- Exposes a FastAPI service for analysis and upload processing
- Includes tests for core chunking behavior and API endpoints

## Supported file types

- PDF
- DOCX
- Markdown (`.md`)
- Text (`.txt`)
- CSV, JSON, HTML, XML, YAML, RTF, LOG
- Images with OCR support (`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.gif`)

## Installation

```bash
pip install -r requirements.txt
```

Or install as a package:

```bash
pip install -e .
```

## Quick start

```bash
python -m autochunk_ai --help
```

Example recommendation:

```bash
python -m autochunk_ai sample.pdf
```

Example chunk generation:

```bash
python -m autochunk_ai sample.md --strategy auto --chunk
```

## Python usage

```python
from utils import choose_chunking_method, chunk_document

recommendation = choose_chunking_method("sample.pdf")
print(recommendation)

chunks = chunk_document("sample.md", strategy="hierarchical", chunk_size=500, overlap=50)
print(len(chunks))
```

## API usage

The FastAPI app exposes an upload-based analysis endpoint:

```bash
uvicorn autochunk_ai.api:app --reload
```

Then upload a document to:

- `POST /api/analyze`

Example fields include:

- `strategy`: `auto`, `hierarchical`, or `recursive`
- `chunk_size`
- `overlap`
- `min_chunk_size`
- `max_chunk_size`
- `max_pages`
- `preserve_headings`

## Error handling

The service handles document and chunk-generation failures explicitly instead of failing silently.

- unsupported or unreadable files are rejected with clear validation messages
- chunk-generation failures are logged server-side
- API responses surface a structured `chunking_error` payload when chunking cannot complete
- internal exception details are kept out of the client-facing response

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

## Notes

The project is designed to support robust chunk recommendation in retrieval pipelines, with explicit handling for ambiguous cases and document-structure-driven selection.
