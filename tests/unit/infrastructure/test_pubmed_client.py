from __future__ import annotations

import json
from typing import TYPE_CHECKING, cast

from src.infrastructure.pubmed_client import PubMedClient

if TYPE_CHECKING:
    from pytest import MonkeyPatch


class StubResponse:
    def __init__(self, *, payload: dict[str, object] | None = None, text: str = "") -> None:
        self._payload = payload or {}
        self.text = text

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return cast("dict[str, object]", json.loads(json.dumps(self._payload)))


def test_fetch_paper_uses_summary_and_abstract_endpoints(monkeypatch: MonkeyPatch) -> None:
    seen_urls: list[str] = []

    def fake_get(url: str, *, timeout: float) -> StubResponse:
        seen_urls.append(url)
        assert timeout == 15.0
        if "esummary.fcgi" in url:
            return StubResponse(
                payload={
                    "result": {
                        "12345678": {
                            "title": "Academic figure planning",
                            "fullauthorname": "Example Author",
                            "fulljournalname": "Journal of Testing",
                            "pubdate": "2026 Jan",
                        }
                    }
                }
            )
        return StubResponse(
            text=(
                "<Abstract>"
                "<AbstractText>One sentence.</AbstractText>"
                "<AbstractText>Second sentence.</AbstractText>"
                "</Abstract>"
            )
        )

    monkeypatch.setattr("src.infrastructure.pubmed_client.httpx.get", fake_get)

    paper = PubMedClient().fetch_paper("12345678")

    assert seen_urls == [
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678&retmode=json",
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=12345678&retmode=xml",
    ]
    assert paper.title == "Academic figure planning"
    assert paper.authors == "Example Author"
    assert paper.journal == "Journal of Testing"
    assert paper.pubdate == "2026 Jan"
    assert paper.abstract == "One sentence. Second sentence."
