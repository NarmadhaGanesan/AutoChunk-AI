# AutoChunk AI web interfaces

This setup adds two browser interfaces to the existing document chunking engine:

- **FastAPI + HTML:** a no-build upload dashboard at `http://127.0.0.1:8000/`.
- **React dashboard:** a Vite/React application with Recharts at `http://127.0.0.1:5173/` during development, or `http://127.0.0.1:8000/react` after building.
- **Dashboard charts:** rule-score visualization, positive/negative evidence breakdown, document statistics, and chunk previews.

The recommendation score is the engine's actual signed structural **rule points**, not a probability or a model confidence estimate. The current recommendation engine uses deterministic rules and recursive fallback for ambiguous scores; this UI does not claim that an LLM made a decision.

## Requirements

- Python 3.10 or later
- Node.js 18 or later and npm (only for the React interface)
- Optional system dependencies for some document formats:
  - DOCX conversion requires Pandoc, as used by the existing `pypandoc` reader.
  - OCR for images requires Tesseract installed on the host in addition to the Python Pillow/pytesseract packages.

## Install and run the FastAPI + HTML interface

From the repository root:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn autochunk_ai.api:app --reload
```

Open <http://127.0.0.1:8000/>. API health check: <http://127.0.0.1:8000/health>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

The upload endpoint is `POST /api/analyze` and uses `multipart/form-data`: `file`, `strategy` (`auto`, `hierarchical`, or `recursive`), `chunk_size`, `overlap`, `min_chunk_size`, `max_chunk_size`, `max_pages`, and `preserve_headings`. Uploads are limited to 15 MiB and accepted only for supported document extensions. The temporary upload is deleted after the request completes.

## Run the React dashboard in development

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173/>. Vite proxies `/api` and `/health` to FastAPI on port 8000, so keep the backend running in the first terminal.

## Build and serve React through FastAPI

```bash
cd frontend
npm install
npm run build
cd ..
uvicorn autochunk_ai.api:app --reload
```

Open <http://127.0.0.1:8000/react>. FastAPI serves the generated `frontend/dist` bundle when it exists. The plain HTML dashboard remains at `/`.

## Recommendation score and chart

The score graph displays the rule-engine score and its two configured decision boundaries: recursive at 1 point or below and hierarchical at 6 points or above. Scores between those boundaries are ambiguous and currently fall back to recursive. Each rule's signed contribution is shown in the evidence list. This is intentionally not converted to a percentage: the engine does not produce calibrated probabilities.

## Notes

- The API analyzes each uploaded document in a temporary file; it does not persist uploads or offer authentication. Run it in a trusted, local environment unless you add deployment-specific access controls and storage policy.
- PDF reading is capped by the `max_pages` setting (30 by default).
- The current service has no LLM credentials or decision callback configured. For ambiguous scores, its existing fallback behavior is preserved.
- To run the existing test suite: `pytest` from the repository root.
