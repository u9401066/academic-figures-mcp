"""Domain entities — objects with business identity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


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
class GenerationManifest:
    """Persisted record of a generation job for reproducibility and replay."""

    manifest_id: str
    asset_kind: str
    figure_type: str
    language: str
    output_size: str
    render_route_requested: str
    render_route_used: str
    prompt: str
    prompt_base: str
    planned_payload: dict[str, Any]
    target_journal: str | None
    journal_profile: dict[str, Any] | None
    source_context: dict[str, Any]
    output_path: str
    model: str
    provider: str
    generation_contract: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    parent_manifest_id: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "asset_kind": self.asset_kind,
            "figure_type": self.figure_type,
            "language": self.language,
            "output_size": self.output_size,
            "render_route_requested": self.render_route_requested,
            "render_route_used": self.render_route_used,
            "prompt": self.prompt,
            "prompt_base": self.prompt_base,
            "planned_payload": dict(self.planned_payload),
            "target_journal": self.target_journal,
            "journal_profile": dict(self.journal_profile) if self.journal_profile else None,
            "source_context": dict(self.source_context),
            "output_path": self.output_path,
            "model": self.model,
            "provider": self.provider,
            "generation_contract": self.generation_contract,
            "created_at": self.created_at.isoformat(),
            "parent_manifest_id": self.parent_manifest_id,
            "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GenerationManifest:
        created_raw = data.get("created_at")
        created_at = (
            datetime.fromisoformat(created_raw)
            if isinstance(created_raw, str)
            else datetime.now(tz=timezone.utc)
        )
        journal_profile = data.get("journal_profile")
        source_context = data.get("source_context") or {}
        planned_payload = data.get("planned_payload") or {}
        warnings = data.get("warnings") or []
        return cls(
            manifest_id=str(data.get("manifest_id") or ""),
            asset_kind=str(data.get("asset_kind") or "generic_visual"),
            figure_type=str(data.get("figure_type") or "infographic"),
            language=str(data.get("language") or "en"),
            output_size=str(data.get("output_size") or "1024x1024"),
            render_route_requested=str(data.get("render_route_requested") or "image_generation"),
            render_route_used=str(data.get("render_route_used") or "image_generation"),
            prompt=str(data.get("prompt") or ""),
            prompt_base=str(data.get("prompt_base") or ""),
            planned_payload=dict(planned_payload),
            target_journal=(
                str(data["target_journal"]).strip() if "target_journal" in data else None
            ),
            journal_profile=dict(journal_profile) if isinstance(journal_profile, dict) else None,
            source_context=dict(source_context) if isinstance(source_context, dict) else {},
            output_path=str(data.get("output_path") or ""),
            model=str(data.get("model") or ""),
            provider=str(data.get("provider") or ""),
            generation_contract=str(data.get("generation_contract") or "planned_payload"),
            created_at=created_at,
            parent_manifest_id=(
                str(data["parent_manifest_id"]).strip() if data.get("parent_manifest_id") else None
            ),
            warnings=[str(item) for item in warnings] if isinstance(warnings, list) else [],
        )


@dataclass
class GenerationJob:
    """Tracks a figure generation request through its lifecycle."""

    job_id: str
    pmid: str
    figure_type: str = "auto"
    language: str = "zh-TW"
    output_size: str = "1024x1536"
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    output_path: str = ""
    error: str = ""
