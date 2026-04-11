"""PubMed E-utilities client — implements domain MetadataFetcher."""

from __future__ import annotations

import json
import re
import urllib.request

from src.domain.entities import Paper
from src.domain.exceptions import PaperNotFoundError
from src.domain.interfaces import MetadataFetcher

_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient(MetadataFetcher):
    """Fetches paper metadata from PubMed using public E-utilities."""

    def fetch_paper(self, pmid: str) -> Paper:
        try:
            summary = self._fetch_summary(pmid)
            summary.abstract = self._fetch_abstract(pmid)
            return summary
        except Exception as exc:
            raise PaperNotFoundError(f"Failed to fetch PMID {pmid}: {exc}") from exc

    # ── Internal helpers ────────────────────────────────────

    @staticmethod
    def _fetch_summary(pmid: str) -> Paper:
        url = f"{_BASE}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        result = data.get("result", {}).get(pmid, {})
        return Paper(
            pmid=pmid,
            title=result.get("title", f"PMID {pmid}"),
            authors=result.get("fullauthorname", ""),
            journal=result.get("fulljournalname", ""),
            pubdate=result.get("pubdate", ""),
        )

    @staticmethod
    def _fetch_abstract(pmid: str) -> str:
        url = f"{_BASE}/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml = resp.read().decode("utf-8")

        abstracts = re.findall(r"<AbstractText[^>]*>(.*?)</AbstractText>", xml, re.DOTALL)
        if abstracts:
            text = " ".join(re.sub(r"<[^>]+>", "", a) for a in abstracts)
            return text[:3000]
        return ""
