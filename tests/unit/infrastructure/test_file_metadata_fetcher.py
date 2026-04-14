from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from src.domain.exceptions import ConfigurationError, PaperNotFoundError
from src.infrastructure.file_metadata_fetcher import FileMetadataFetcher

if TYPE_CHECKING:
    from pathlib import Path


def test_file_metadata_fetcher_reads_yaml_papers_list(tmp_path: Path) -> None:
    data_file = tmp_path / "papers.yaml"
    data_file.write_text(
        """
papers:
  - pmid: "12345678"
    title: Academic figure planning
    authors:
      - Example Author
      - Second Author
    journal: Journal of Testing
    pubdate: 2026 Jan
    abstract: Workflow summary for publication-ready figures.
""".strip(),
        encoding="utf-8",
    )

    fetcher = FileMetadataFetcher(data_file)
    paper = fetcher.fetch_paper("12345678")

    assert paper.title == "Academic figure planning"
    assert paper.authors == "Example Author, Second Author"
    assert paper.journal == "Journal of Testing"
    assert paper.abstract == "Workflow summary for publication-ready figures."


def test_file_metadata_fetcher_reads_json_mapping(tmp_path: Path) -> None:
    data_file = tmp_path / "papers.json"
    data_file.write_text(
        json.dumps(
            {
                "41657234": {
                    "title": "Airway rescue workflow",
                    "authors": "Example Author",
                    "journal": "Journal of Testing",
                    "abstract": "A structured airway rescue algorithm.",
                }
            }
        ),
        encoding="utf-8",
    )

    fetcher = FileMetadataFetcher(data_file)
    paper = fetcher.fetch_paper("41657234")

    assert paper.pmid == "41657234"
    assert paper.title == "Airway rescue workflow"


def test_file_metadata_fetcher_raises_for_missing_pmid(tmp_path: Path) -> None:
    data_file = tmp_path / "papers.yaml"
    data_file.write_text("papers: [{pmid: '1', title: test}]", encoding="utf-8")

    fetcher = FileMetadataFetcher(data_file)

    with pytest.raises(PaperNotFoundError, match="PMID 999 not found"):
        fetcher.fetch_paper("999")


def test_file_metadata_fetcher_raises_for_invalid_file_shape(tmp_path: Path) -> None:
    data_file = tmp_path / "papers.yaml"
    data_file.write_text("papers: []", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="at least one paper"):
        FileMetadataFetcher(data_file)
