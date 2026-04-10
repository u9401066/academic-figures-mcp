"""Domain entities — objects with business identity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Paper:
    """Paper metadata from PubMed or user input."""

    pmid: str
    title: str = ""
    authors: str = ""
    journal: str = ""
    pubdate: str = ""
    abstract: str = ""


@dataclass
class GenerationResult:
    """Result of an image generation or editing call."""

    image_bytes: bytes | None = None
    text: str = ""
    model: str = ""
    elapsed_seconds: float = 0.0
    error: str = ""
    media_type: str = "image/png"

    @property
    def ok(self) -> bool:
        return self.image_bytes is not None and not self.error

    @property
    def file_extension(self) -> str:
        if self.media_type == "image/svg+xml":
            return ".svg"
        if self.media_type == "image/jpeg":
            return ".jpg"
        return ".png"

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if self.image_bytes:
            p.write_bytes(self.image_bytes)
        return p


@dataclass
class GenerationJob:
    """Tracks a figure generation request through its lifecycle."""

    job_id: str
    pmid: str
    figure_type: str = "auto"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    output_path: str = ""
    error: str = ""
