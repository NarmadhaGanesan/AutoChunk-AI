from autochunk_ai import service as service_module
from autochunk_ai.service import AutoChunkService


def test_analyze_document_reports_chunking_failure(monkeypatch, caplog):
    monkeypatch.setattr(
        service_module,
        "_choose_chunking_method",
        lambda *_args, **_kwargs: {
            "chunking_method": "recursive",
            "reason": "test recommendation",
        },
    )

    def fail_chunking(*_args, **_kwargs):
        raise ValueError("internal parser detail")

    monkeypatch.setattr(service_module, "_chunk_document", fail_chunking)

    result = AutoChunkService().analyze_document("document.txt")

    assert result["chunk_count"] == 0
    assert result["chunks"] == []
    assert result["chunking_error"] == {
        "code": "chunking_failed",
        "message": "Chunk generation failed; see server logs for details.",
    }
    assert "internal parser detail" not in result["chunking_error"]["message"]
    assert "Chunk generation failed during document analysis" in caplog.text
