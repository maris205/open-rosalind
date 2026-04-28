"""UniProt tools: fetch and search."""
import requests


def fetch(accession: str) -> dict:
    """Fetch UniProt entry by accession."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    return {
        "id": data.get("uniProtkbId"),
        "accession": data["primaryAccession"],
        "name": data["proteinDescription"]["recommendedName"]["fullName"]["value"],
        "organism": data["organism"]["scientificName"],
        "function": data.get("comments", [{}])[0].get("texts", [{}])[0].get("value", ""),
        "sequence": data["sequence"]["value"],
        "length": data["sequence"]["length"],
    }


def search(query: str, max_results: int = 10) -> dict:
    """Search UniProt by query string."""
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {"query": query, "size": max_results, "format": "json"}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    hits = []
    for result in data.get("results", []):
        hits.append({
            "accession": result["primaryAccession"],
            "name": result["proteinDescription"]["recommendedName"]["fullName"]["value"],
            "organism": result["organism"]["scientificName"],
            "score": result.get("score", 0),
        })

    return {"hits": hits, "count": len(hits)}
