from fastapi.testclient import TestClient

from autochunk_ai.api import app

client = TestClient(app)


def _analysis_data(**overrides):
    data = {
        "strategy": "auto",
        "chunk_size": "500",
        "overlap": "50",
        "min_chunk_size": "100",
        "max_chunk_size": "800",
        "max_pages": "30",
        "preserve_headings": "true",
    }
    data.update(overrides)
    return data


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_upload_accepts_markdown():
    content = b"# Project Overview\n\nThis file explains the team workflow.\n\n## Background\n\nThe first launch was a success.\n\n### Scope\n\nWe validate with a simple review loop.\n"

    response = client.post(
        "/api/analyze",
        files={"file": ("sample.md", content, "text/markdown")},
        data=_analysis_data(),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["filename"] == "sample.md"
    assert payload["recommendation"] in {"hierarchical", "recursive"}
    assert payload["strategy"] in {"hierarchical", "recursive"}
    assert len(payload["chunks"]) >= 1
    assert payload["stats"]["chunk_count"] == len(payload["chunks"])


def test_analyze_upload_rejects_empty_file():
    response = client.post(
        "/api/analyze",
        files={"file": ("empty.md", b"", "text/markdown")},
        data=_analysis_data(),
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_upload_rejects_unsupported_extension():
    response = client.post(
        "/api/analyze",
        files={"file": ("archive.bin", b"not a real document", "application/octet-stream")},
        data=_analysis_data(),
    )

    assert response.status_code == 415
    assert "Unsupported file extension" in response.json()["detail"]
