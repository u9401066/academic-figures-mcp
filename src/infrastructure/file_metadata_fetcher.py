"""File-backed metadata fetcher for offline demos, smoke tests, and fixed corpora."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from src.domain.entities import Paper
from src.domain.exceptions import ConfigurationError, PaperNotFoundError
from src.domain.interfaces import MetadataFetcher


class FileMetadataFetcher(MetadataFetcher):
    """Loads normalized Paper records from a local JSON or YAML file."""

    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path).expanduser()
        self._papers = self._load_papers(self._file_path)

    def fetch_paper(self, pmid: str) -> Paper:
        paper = self._papers.get(pmid)
        if paper is None:
            raise PaperNotFoundError(f"PMID {pmid} not found in metadata file {self._file_path}")
        return paper

    def _load_papers(self, file_path: Path) -> dict[str, Paper]:
        if not file_path.exists():
            raise ConfigurationError(f"Metadata file not found: {file_path}")

        try:
            raw_data = self._read_file(file_path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            raise ConfigurationError(f"Failed to load metadata file {file_path}: {exc}") from exc

        records = self._extract_records(raw_data)
        papers: dict[str, Paper] = {}
        for record in records:
            paper = self._record_to_paper(record)
            if paper is None:
                continue
            papers[paper.pmid] = paper

        if not papers:
            raise ConfigurationError(
                "Metadata file must contain at least one paper with a non-empty pmid"
            )
        return papers

    @staticmethod
    def _read_file(file_path: Path) -> object:
        content = file_path.read_text(encoding="utf-8")
        if file_path.suffix.lower() == ".json":
            return json.loads(content)
        return yaml.safe_load(content)

    @staticmethod
    def _extract_records(raw_data: object) -> list[dict[str, Any]]:
        if isinstance(raw_data, list):
            return [item for item in raw_data if isinstance(item, dict)]

        if not isinstance(raw_data, dict):
            return []

        papers = raw_data.get("papers")
        if isinstance(papers, list):
            return [item for item in papers if isinstance(item, dict)]

        if "pmid" in raw_data:
            return [raw_data]

        records: list[dict[str, Any]] = []
        for pmid, value in raw_data.items():
            if not isinstance(value, dict):
                continue
            record = dict(value)
            record.setdefault("pmid", str(pmid))
            records.append(record)
        return records

    @staticmethod
    def _record_to_paper(record: dict[str, Any]) -> Paper | None:
        pmid = str(record.get("pmid") or "").strip()
        if not pmid:
            return None
        return Paper(
            pmid=pmid,
            title=FileMetadataFetcher._as_text(record.get("title")),
            authors=FileMetadataFetcher._as_text(record.get("authors")),
            journal=FileMetadataFetcher._as_text(record.get("journal")),
            pubdate=FileMetadataFetcher._as_text(record.get("pubdate")),
            abstract=FileMetadataFetcher._as_text(record.get("abstract")),
        )

    @staticmethod
    def _as_text(value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "").strip()
