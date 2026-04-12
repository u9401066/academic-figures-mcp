from __future__ import annotations

import httpx
import pytest

from src.domain.exceptions import PaperNotFoundError
from src.infrastructure.pubmed_client import PubMedClient


def test_pubmed_client_fetch_paper_parses_summary_and_abstract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            httpx.Response(
                200,
                text=(
                    '{"result":{"123":{"title":"Paper Title","fullauthorname":"A. Author",'
                    '"fulljournalname":"Journal","pubdate":"2026"}}}'
                ),
                request=httpx.Request("GET", "https://example.test/esummary"),
            ),
            httpx.Response(
                200,
                text="<Abstract><AbstractText>First <b>result</b>.</AbstractText></Abstract>",
                request=httpx.Request("GET", "https://example.test/efetch"),
            ),
        ]
    )

    monkeypatch.setattr(
        "src.infrastructure.pubmed_client.httpx.get",
        lambda *args, **kwargs: next(responses),
    )

    paper = PubMedClient().fetch_paper("123")

    assert paper.pmid == "123"
    assert paper.title == "Paper Title"
    assert paper.authors == "A. Author"
    assert paper.journal == "Journal"
    assert paper.pubdate == "2026"
    assert paper.abstract == "First result."


def test_pubmed_client_wraps_request_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_get(*args: object, **kwargs: object) -> httpx.Response:
        raise httpx.HTTPError("network down")

    monkeypatch.setattr("src.infrastructure.pubmed_client.httpx.get", fail_get)

    with pytest.raises(PaperNotFoundError):
        PubMedClient().fetch_paper("123")
