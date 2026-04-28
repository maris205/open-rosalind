"""PubMed search tools."""
import requests


def search(query: str, max_results: int = 10) -> dict:
    """Search PubMed."""
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {"db": "pubmed", "term": query, "retmax": max_results, "retmode": "json"}
    resp = requests.get(search_url, params=params, timeout=10)
    resp.raise_for_status()
    pmids = resp.json()["esearchresult"]["idlist"]

    if not pmids:
        return {"hits": [], "count": 0}

    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    resp = requests.get(fetch_url, params={"db": "pubmed", "id": ",".join(pmids), "rettype": "abstract", "retmode": "xml"}, timeout=10)
    resp.raise_for_status()

    import xml.etree.ElementTree as ET
    root = ET.fromstring(resp.content)
    hits = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")
        title = article.findtext(".//ArticleTitle") or ""
        abstract = article.findtext(".//AbstractText") or ""
        hits.append({"pmid": pmid, "title": title, "abstract": abstract})

    return {"hits": hits, "count": len(hits)}
