"""FastAPI endpoints and lightweight web frontends for AutoChunk AI."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from utils import add_up_rule_points, chunk_document, choose_chunking_method, read_document

app = FastAPI(
    title="AutoChunk AI",
    description="Analyze document structure and preview generated chunks.",
    version="1.1.0",
)

ROOT = Path(__file__).resolve().parent.parent
HTML_INDEX = ROOT / "web" / "index.html"
REACT_DIST = ROOT / "frontend" / "dist"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".md", ".txt", ".csv", ".json", ".html", ".htm",
    ".xml", ".rtf", ".log", ".yaml", ".yml", ".jpg", ".jpeg", ".png",
    ".tif", ".tiff", ".bmp", ".gif",
}

if (REACT_DIST / "assets").is_dir():
    app.mount("/react-assets", StaticFiles(directory=REACT_DIST / "assets"), name="react-assets")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def html_frontend() -> FileResponse:
    return FileResponse(HTML_INDEX)


@app.get("/react", include_in_schema=False)
def react_frontend() -> FileResponse | JSONResponse:
    index = REACT_DIST / "index.html"
    if not index.is_file():
        return JSONResponse(
            status_code=404,
            content={
                "detail": "React UI is not built yet. Follow the frontend build steps in UI_SETUP.md, then open /react."
            },
        )
    return FileResponse(index)


def _analyze_saved_file(
    path: str,
    display_name: str,
    strategy: str,
    chunk_size: int,
    overlap: int,
    min_chunk_size: int,
    max_chunk_size: int,
    max_pages: int,
    preserve_headings: bool,
) -> dict[str, Any]:
    recommendation = choose_chunking_method(path, max_pages=max_pages)
    document = read_document(path, max_pages=max_pages)
    score, matched_rules = add_up_rule_points(document)
    effective_strategy = (
        recommendation.get("chunking_method", "recursive") if strategy == "auto" else strategy
    )
    chunks = chunk_document(
        path,
        strategy=effective_strategy,
        chunk_size=chunk_size,
        overlap=overlap,
        min_chunk_size=min_chunk_size,
        max_chunk_size=max_chunk_size,
        preserve_headings=preserve_headings,
        max_pages=max_pages,
    )

    return {
        "filename": display_name,
        "recommendation": recommendation.get("chunking_method", "recursive"),
        "strategy": effective_strategy,
        "reason": recommendation.get("reason", "No explanation was returned."),
        "rule_score": score,
        "score_label": "Rule points (not a probability)",
        "thresholds": {"recursive_at_or_below": 1, "hierarchical_at_or_above": 6},
        "rules": [
            {"description": description, "points": points}
            for description, points in matched_rules
        ],
        "stats": {
            "pages_read": document.pages_read,
            "total_pages": document.total_pages,
            "lines": len(document.lines),
            "tokens": document.total_tokens,
            "chunk_count": len(chunks),
            "average_chunk_tokens": round(sum(c.token_count for c in chunks) / len(chunks)) if chunks else 0,
        },
        "chunks": [
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
        ],
    }


@app.post("/api/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    strategy: str = Form("auto"),
    chunk_size: int = Form(500, ge=1, le=10000),
    overlap: int = Form(50, ge=0, le=9999),
    min_chunk_size: int = Form(100, ge=1, le=10000),
    max_chunk_size: int = Form(800, ge=1, le=20000),
    max_pages: int = Form(30, ge=1, le=500),
    preserve_headings: bool = Form(True),
) -> dict[str, Any]:
    """Analyze an uploaded document without trusting its submitted filename/path."""
    if strategy not in {"auto", "hierarchical", "recursive"}:
        raise HTTPException(status_code=422, detail="strategy must be auto, hierarchical, or recursive")

    filename = Path(file.filename or "document").name
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file extension: {suffix or '(none)'}")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds the 15 MiB limit.")

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="autochunk-", suffix=suffix, delete=False) as temp:
            temp.write(data)
            temporary_path = temp.name
        return await run_in_threadpool(
            _analyze_saved_file,
            temporary_path,
            filename,
            strategy,
            chunk_size,
            overlap,
            min_chunk_size,
            max_chunk_size,
            max_pages,
            preserve_headings,
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Do not expose server paths or stack traces to the browser.
        message = re.sub(r"\s+", " ", str(exc)).strip() or type(exc).__name__
        raise HTTPException(status_code=422, detail=f"Could not analyze this document: {message}") from exc
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
        await file.close()


__all__ = ["app"]
