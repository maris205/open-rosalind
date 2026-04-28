"""Literature search handler."""
from . import tools

def handler(payload: dict, trace) -> dict:
    query = payload.get("query", "").strip()
    if not query:
        return {"annotation": {"kind": "literature"}, "confidence": 0.0, "notes": ["Empty query"], "pubmed": {}}
    
    try:
        results = tools.search(query=query, max_results=10)
        return {
            "annotation": {"kind": "literature", "query": query, "n_hits": results["count"], "top_pmids": [h["pmid"] for h in results["hits"][:3]]},
            "confidence": 0.8 if results["count"] > 0 else 0.0,
            "notes": [],
            "pubmed": results,
        }
    except Exception as e:
        return {"annotation": {"kind": "literature"}, "confidence": 0.0, "notes": [f"Search failed: {e}"], "pubmed": {}}
