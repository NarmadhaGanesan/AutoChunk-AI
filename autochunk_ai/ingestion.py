"""Knowledge base implementation for AutoChunk AI."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

try:
    from utils import chunk_document
except Exception:  # pragma: no cover - fallback when the project is imported as a package
    chunk_document = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", (text or "").lower())


@dataclass
class KnowledgeEntry:
    """A single indexed chunk stored in the knowledge base."""

    id: str
    source_path: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chunk_index: int = 0
    strategy: str = "auto"
    token_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "KnowledgeEntry":
        return cls(
            id=str(payload.get("id") or payload.get("source_path") or "entry"),
            source_path=str(payload.get("source_path", "")),
            text=str(payload.get("text", "")),
            metadata=dict(payload.get("metadata") or {}),
            chunk_index=int(payload.get("chunk_index", 0)),
            strategy=str(payload.get("strategy", "auto")),
            token_count=int(payload.get("token_count", 0)),
        )


class KnowledgeBase:
    """Simple local knowledge base backed by JSON persistence and cosine-style retrieval."""

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

    def __init__(self, storage_path: str | Path | None = None, *, records: Sequence[KnowledgeEntry] | None = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.records: list[KnowledgeEntry] = list(records or [])

    def add_entry(self, entry: KnowledgeEntry | dict[str, Any]) -> KnowledgeEntry:
        normalized = KnowledgeEntry.from_dict(entry) if isinstance(entry, dict) else entry
        if not normalized.id:
            normalized.id = f"{normalized.source_path}:{normalized.chunk_index}"
        self.records.append(normalized)
        return normalized

    def ingest_document(
        self,
        path: str | Path,
        *,
        strategy: str = "auto",
        chunk_size: int = 500,
        overlap: int = 50,
        min_chunk_size: int = 100,
        max_chunk_size: int = 800,
        preserve_headings: bool = True,
        max_pages: int = 30,
        metadata: dict[str, Any] | None = None,
    ) -> list[KnowledgeEntry]:
        if chunk_document is None:
            raise RuntimeError("chunk_document is not available. Ensure the project utilities can be imported.")

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

        ingested: list[KnowledgeEntry] = []
        base_metadata = dict(metadata or {})
        for chunk in chunks:
            entry = KnowledgeEntry(
                id=f"{Path(path).resolve()}:{chunk.chunk_index}",
                source_path=str(path),
                text=(chunk.text or "").strip(),
                metadata={**base_metadata, **(chunk.metadata or {})},
                chunk_index=chunk.chunk_index,
                strategy=chunk.strategy,
                token_count=int(getattr(chunk, "token_count", 0) or 0),
            )
            self.add_entry(entry)
            ingested.append(entry)
        return ingested

    def ingest_folder(
        self,
        folder_path: str | Path,
        *,
        recursive: bool = True,
        **kwargs: Any,
    ) -> list[KnowledgeEntry]:
        root = Path(folder_path)
        if not root.exists():
            raise FileNotFoundError(f"Folder does not exist: {root}")

        added: list[KnowledgeEntry] = []
        iterator = root.rglob("*") if recursive else root.iterdir()
        for candidate in sorted(iterator, key=lambda p: str(p).lower()):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue
            added.extend(self.ingest_document(candidate, **kwargs))
        return added

    def save(self, path: str | Path | None = None) -> str:
        target = Path(path or self.storage_path or "autochunk_kb.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {"records": [record.to_dict() for record in self.records]}
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.storage_path = target
        return str(target)

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeBase":
        target = Path(path)
        if not target.exists():
            return cls(storage_path=target, records=[])
        payload = json.loads(target.read_text(encoding="utf-8"))
        records = [KnowledgeEntry.from_dict(item) for item in payload.get("records", [])]
        return cls(storage_path=target, records=records)

    def search(self, query: str, *, top_k: int = 5, min_score: float = 0.0) -> list[dict[str, Any]]:
        if not query or not self.records:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        vocab = sorted({token for record in self.records for token in _tokenize(record.text)})
        if not vocab:
            return []

        total_docs = len(self.records)
        idf: dict[str, float] = {}
        for token in vocab:
            doc_count = sum(1 for record in self.records if token in _tokenize(record.text))
            idf[token] = 1.0 + (total_docs / max(1, doc_count))

        def vector_for(text: str) -> dict[str, float]:
            counts: dict[str, int] = {}
            for token in _tokenize(text):
                counts[token] = counts.get(token, 0) + 1
            total = sum(counts.values())
            if total == 0:
                return {}
            return {token: (count / total) * idf.get(token, 1.0) for token, count in counts.items()}

        query_vector = vector_for(query)
        if not query_vector:
            return []

        scored: list[tuple[float, KnowledgeEntry]] = []
        for record in self.records:
            record_vector = vector_for(record.text)
            if not record_vector:
                continue
            numerator = sum(query_vector.get(token, 0.0) * value for token, value in record_vector.items())
            q_norm = (sum(v * v for v in query_vector.values())) ** 0.5
            r_norm = (sum(v * v for v in record_vector.values())) ** 0.5
            denom = q_norm * r_norm
            score = numerator / denom if denom else 0.0
            if score >= min_score:
                scored.append((score, record))

        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[dict[str, Any]] = []
        for score, record in scored[: max(1, top_k)]:
            results.append(
                {
                    "id": record.id,
                    "source_path": record.source_path,
                    "chunk_index": record.chunk_index,
                    "strategy": record.strategy,
                    "score": round(float(score), 4),
                    "text": record.text,
                    "metadata": record.metadata,
                }
            )
        return results

    def __len__(self) -> int:
        return len(self.records)


__all__ = ["KnowledgeBase", "KnowledgeEntry"]
