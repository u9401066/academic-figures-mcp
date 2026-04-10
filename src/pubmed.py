"""
PubMed metadata fetcher using E-utilities API.
No API key required for basic access.
"""

import json
import urllib.request
from typing import Optional


def fetch_paper(pmid: str) -> dict:
    """Fetch paper metadata from PubMed.

    Returns dict with: pmid, title, authors, journal, pubdate, abstract
    """
    try:
        result = fetch_summary(pmid)
        abstract = fetch_abstract(pmid)
        result["abstract"] = abstract
        return result
    except Exception as e:
        return {"error": f"Failed to fetch PMID {pmid}: {str(e)}", "pmid": pmid}


def fetch_summary(pmid: str) -> dict:
    """Basic paper summary from E-utilities esummary."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    url = f"{base}/esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    result = data.get("result", {}).get(pmid, {})
    return {
        "pmid": pmid,
        "title": result.get("title", f"PMID {pmid}"),
        "authors": result.get("fullauthorname", ""),
        "journal": result.get("fulljournalname", ""),
        "pubdate": result.get("pubdate", ""),
    }


def fetch_abstract(pmid: str) -> str:
    """Fetch abstract text from PubMed."""
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    url = f"{base}/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml"
    with urllib.request.urlopen(url, timeout=15) as resp:
        xml = resp.read().decode("utf-8")

    # Extract abstract text from XML (simple parser)
    import re
    abstracts = re.findall(r'<AbstractText[^>]*>(.*?)</AbstractText>', xml, re.DOTALL)
    if abstracts:
        # Clean HTML/XML tags
        text = " ".join(re.sub(r'<[^>]+>', '', a) for a in abstracts)
        return text[:3000]  # truncate to avoid token overload
    return ""
