<div align="center">

# 🧩 AutoChunk-AI

### Make every document retrieval-ready.

**Automatically analyze document structure, choose the smarter chunking strategy, and turn files into contextual AI-ready chunks.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-Dashboard-61DAFB?logo=react&logoColor=20232A)](https://react.dev/)
[![License](https://img.shields.io/badge/License-Research%20%26%20Experimentation-blueviolet)](#-license)

[Quick Start](#-quick-start) • [Web Interfaces](#-web-interfaces) • [Python API](#-python-api) • [CLI](#-command-line) • [Documentation](#-project-map)

</div>

---

## ✨ What is AutoChunk-AI?

Not all documents are built the same. A policy manual, research paper, email dump, and scanned report each deserve a different chunking strategy.

**AutoChunk-AI inspects document structure and decides:**

| Strategy | Best fit | How it behaves |
|---|---|---|
| **Hierarchical** | Heading-rich reports, manuals, papers | Preserves headings and document hierarchy |
| **Recursive** | Flat or loosely structured text | Splits progressively using natural boundaries |
| **Automatic** | Any document | Uses rule-based structural scoring, with existing fallback behavior for ambiguous cases |

> The recommendation score is signed structural rule evidence—not a probability or model confidence score.

```text
Document
   │
   ├── Detect headings, numbering, bookmarks, formatting & text structure
   │
   ├── Add structural rule points
   │
   ├── ≤ 1 → Recursive
   ├── 2–5 → Ambiguous / existing fallback
   └── ≥ 6 → Hierarchical
   │
   ▼
Retrieval-ready chunks
```

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/NarmadhaGanesan/AutoChunk-AI.git
cd AutoChunk-AI
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Start the application

```bash
uvicorn autochunk_ai.api:app --reload
```

Open:

- **Dashboard:** <http://127.0.0.1:8000/>
- **API docs:** <http://127.0.0.1:8000/docs>
- **Health check:** <http://127.0.0.1:8000/health>

---

## 🖥️ Web Interfaces

AutoChunk-AI includes two browser experiences.

### Lightweight HTML dashboard

A no-build interface for instantly uploading documents and inspecting recommendations.

```text
http://127.0.0.1:8000/
```

### React dashboard

A richer interface with visualization and chunk previews.

```bash
cd frontend
npm install
npm run dev
```

Development URL:

```text
http://127.0.0.1:5173/
```

Or build it into the FastAPI application:

```bash
cd frontend
npm install
npm run build
cd ..
uvicorn autochunk_ai.api:app --reload
```

Production-style React URL:

```text
http://127.0.0.1:8000/react
```

The dashboard surfaces:

- Structural rule points and decision boundaries
- Positive and negative evidence
- Document statistics
- Chunk previews
- Configurable chunk size, overlap, and heading preservation

---

## 💻 Command Line

Analyze a document:

```bash
python -m autochunk_ai sample.pdf
```

Generate chunks automatically:

```bash
python -m autochunk_ai sample.md --strategy auto --chunk
```

Control chunk parameters:

```bash
python -m autochunk_ai sample.pdf --strategy hierarchical --chunk \
  --chunk-size 500 --overlap 50 --min-chunk-size 100 --max-chunk-size 800 \
  --max-pages 30 --out results.json
```

Run `python -m autochunk_ai --help` to see every available option.

---

## 🐍 Python API

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

print(f"Generated {len(chunks)} chunks")
```

### FastAPI endpoint

Upload a document and receive a recommendation, chunk preview, rule evidence, and document statistics.

```text
POST /api/analyze
Content-Type: multipart/form-data
```

| Field | Default | Description |
|---|---:|---|
| `file` | Required | Document to analyze |
| `strategy` | `auto` | `auto`, `hierarchical`, or `recursive` |
| `chunk_size` | `500` | Desired chunk size |
| `overlap` | `50` | Overlap between adjacent chunks |
| `min_chunk_size` | `100` | Minimum chunk size |
| `max_chunk_size` | `800` | Maximum chunk size |
| `max_pages` | `30` | Maximum PDF pages to process |
| `preserve_headings` | `true` | Preserve heading context |

Example with `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/analyze" \
  -F "file=@sample.pdf" \
  -F "strategy=auto" \
  -F "chunk_size=500" \
  -F "overlap=50"
```

---

## 📚 Supported Formats

| Category | Formats |
|---|---|
| **Documents** | PDF, DOCX |
| **Text & data** | Markdown, TXT, CSV, JSON, HTML, XML, YAML, RTF, LOG |
| **Images / OCR** | JPG, JPEG, PNG, BMP, TIFF, GIF |

### Optional system dependencies

- **DOCX conversion:** Pandoc
- **Image OCR:** Tesseract

PDF processing is capped by `max_pages`; the default is 30 pages.

Uploads are limited to **15 MiB** and stored only temporarily during analysis.

---

## 🧪 Testing

```bash
pytest
```

The test suite covers core chunking behavior and API endpoints.

---

## 🗺️ Project Map

```text
.
├── autochunk_ai/          # Recommendation engine, ingestion, chunking & API
│   ├── api.py
│   ├── chunking.py
│   ├── ingestion.py
│   ├── scoring.py
│   └── service.py
├── frontend/              # React + Vite dashboard
├── web/                   # Lightweight HTML dashboard
├── tests/                 # Core and API tests
├── constants.py
├── models.py
├── utils.py
├── pyproject.toml
├── requirements.txt
└── UI_SETUP.md
```

---

## 🔒 Running Safely

- The API does not persist uploaded files.
- There is no built-in authentication or authorization.
- Run locally or in a trusted environment unless deployment-specific access controls are added.
- Internal exception details are not exposed in client-facing API responses.
- The current service has no configured LLM credentials or decision callback; ambiguous scores retain the existing fallback behavior.

---

## 📜 License

This project is intended for **research and experimentation** in document-aware AI retrieval workflows.

<div align="center">

### Built to help documents find the structure they deserve.

[⬆ Back to top](#-autochunk-ai)

</div>
