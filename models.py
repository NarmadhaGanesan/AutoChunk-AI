"""Data models used by the standalone chunking-method recommender."""

from dataclasses import dataclass, field
from typing import Literal

try:
    from pydantic import BaseModel, Field

    class ChunkingMethodDecision(BaseModel):
        """Optional structured result for an LLM decision."""
        chunking_method: Literal["hierarchical", "recursive"] = Field(
            description="The chunking method that fits the document"
        )
        confidence: float = Field(
            ge=0.0,
            le=1.0,
            description="Confidence in the selected method, from 0.0 to 1.0",
        )
except ImportError:
    @dataclass
    class ChunkingMethodDecision:
        """Fallback model if Pydantic is not installed."""
        chunking_method: Literal["hierarchical", "recursive"]
        confidence: float


@dataclass
class Line:
    text: str
    page: int
    size: float = 0.0
    bold: float = 0.0
    tokens: int = 0
    offset: int = 0


@dataclass
class Doc:
    path: str
    total_pages: int
    pages_read: int
    lines: list[Line] = field(default_factory=list)
    bookmarks: list[tuple[int, str]] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(line.tokens for line in self.lines)
