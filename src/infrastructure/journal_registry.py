"""YAML-backed journal requirement registry for prompt injection."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path


class JournalRegistry:
    """Loads journal requirement profiles and resolves them from free-text names."""

    def __init__(self, registry_path: Path) -> None:
        self._profiles: list[dict[str, Any]] = []
        self._aliases: list[tuple[str, dict[str, Any]]] = []
        self._load_registry(registry_path)

    def resolve_profile(
        self,
        *,
        target_journal: str | None = None,
        source_journal: str | None = None,
    ) -> dict[str, Any] | None:
        for match_type, candidate in (
            ("target_journal", target_journal),
            ("source_journal", source_journal),
        ):
            matched = self._match(candidate)
            if matched is None:
                continue
            profile = deepcopy(matched)
            profile["matched_by"] = match_type
            profile["matched_on"] = candidate.strip() if isinstance(candidate, str) else ""
            return profile
        return None

    def _load_registry(self, registry_path: Path) -> None:
        if not registry_path.exists():
            return

        raw_data = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            return

        raw_profiles = raw_data.get("profiles")
        if not isinstance(raw_profiles, list):
            return

        for raw_profile in raw_profiles:
            if not isinstance(raw_profile, dict):
                continue
            profile_id = raw_profile.get("id")
            if not isinstance(profile_id, str) or not profile_id.strip():
                continue

            profile = dict(raw_profile)
            profile["id"] = profile_id.strip()
            self._profiles.append(profile)

            for alias in self._build_aliases(profile):
                self._aliases.append((alias, profile))

        self._aliases.sort(key=lambda item: len(item[0]), reverse=True)

    def _build_aliases(self, profile: dict[str, Any]) -> list[str]:
        raw_aliases = []
        raw_aliases.append(profile.get("id"))
        raw_aliases.append(profile.get("display_name"))

        aliases = profile.get("aliases")
        if isinstance(aliases, list):
            raw_aliases.extend(aliases)

        normalized_aliases: list[str] = []
        seen: set[str] = set()
        for raw_alias in raw_aliases:
            normalized = self._normalize(raw_alias)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            normalized_aliases.append(normalized)
        return normalized_aliases

    def _match(self, candidate: str | None) -> dict[str, Any] | None:
        normalized_candidate = self._normalize(candidate)
        if not normalized_candidate:
            return None

        for alias, profile in self._aliases:
            if normalized_candidate == alias:
                return profile

        for alias, profile in self._aliases:
            if len(alias) < 4:
                continue
            if alias in normalized_candidate or normalized_candidate in alias:
                return profile

        return None

    @staticmethod
    def _normalize(value: object) -> str:
        if not isinstance(value, str):
            return ""
        normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
        return " ".join(normalized.split())
