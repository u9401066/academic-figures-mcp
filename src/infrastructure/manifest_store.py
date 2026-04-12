"""File-backed manifest store for generation reproducibility."""

from __future__ import annotations

import builtins
import json
from pathlib import Path

from src.domain.entities import GenerationManifest
from src.domain.exceptions import ManifestNotFoundError
from src.domain.interfaces import ManifestStore


class FileManifestStore(ManifestStore):
    """Persists manifests as JSON files under a configurable root directory."""

    def __init__(self, root_dir: str = ".academic-figures/manifests") -> None:
        self._root = Path(root_dir)

    def save(self, manifest: GenerationManifest) -> GenerationManifest:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / f"{manifest.manifest_id}.json"
        path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        return manifest

    def load(self, manifest_id: str) -> GenerationManifest:
        path = self._root / f"{manifest_id}.json"
        if not path.exists():
            raise ManifestNotFoundError(f"Manifest not found: {manifest_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return GenerationManifest.from_dict(data)

    def list(self, limit: int = 20) -> builtins.list[GenerationManifest]:
        manifests: builtins.list[GenerationManifest] = []
        for path in self._iter_paths(limit):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                manifests.append(GenerationManifest.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue
        return manifests

    def _iter_paths(self, limit: int) -> builtins.list[Path]:
        if not self._root.exists():
            return []
        files = sorted(
            self._root.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if limit <= 0:
            return files
        return files[:limit]
