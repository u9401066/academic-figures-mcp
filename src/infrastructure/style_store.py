"""File-backed style profile store for Theme 4: Style Intelligence."""

from __future__ import annotations

import json
from pathlib import Path

from src.domain.exceptions import StyleNotFoundError
from src.domain.interfaces import StyleStore
from src.domain.value_objects import StyleProfile


class FileStyleStore(StyleStore):
    """Persists ``StyleProfile`` objects as JSON files on disk."""

    def __init__(self, base_dir: str = ".academic-figures/styles") -> None:
        self._base_dir = Path(base_dir)

    def save(self, profile: object) -> object:
        if not isinstance(profile, StyleProfile):
            raise TypeError("profile must be a StyleProfile instance")
        self._base_dir.mkdir(parents=True, exist_ok=True)
        path = self._base_dir / f"{profile.style_id}.json"
        data = profile.to_dict()
        data["raw_extraction_text"] = profile.raw_extraction_text
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return profile

    def load(self, style_id: str) -> object:
        path = self._base_dir / f"{style_id}.json"
        if not path.exists():
            raise StyleNotFoundError(f"Style profile not found: {style_id}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return StyleProfile.from_dict(data)

    def list(self, limit: int = 20) -> list[object]:
        if not self._base_dir.exists():
            return []
        files = sorted(
            self._base_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        profiles: list[object] = []
        for f in files[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                profiles.append(StyleProfile.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return profiles
