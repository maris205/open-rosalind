"""gnomAD GraphQL client."""
from __future__ import annotations

from typing import Any

from ._http import post_json
from .base import ToolSpec

ENDPOINT = "https://gnomad.broadinstitute.org/api"

VARIANT_QUERY = """
query Variant($variantId: String, $rsid: String, $dataset: DatasetId!) {
  variant(variantId: $variantId, rsid: $rsid, dataset: $dataset) {
    variantId
    reference_genome
    exome { ac an af }
    genome { ac an af }
    sortedTranscriptConsequences {
      gene_symbol
      major_consequence
      transcript_id
      hgvs
    }
  }
}
"""


def fetch_variant(variant_id: str | None = None, rsid: str | None = None, dataset: str = "gnomad_r4") -> dict[str, Any]:
    """Fetch a gnomAD variant summary by variantId or rsID."""
    clean_variant_id = (variant_id or "").strip()
    clean_rsid = (rsid or "").strip()
    if not clean_variant_id and not clean_rsid:
        raise ValueError("variant_id or rsid is required")

    data = post_json(
        ENDPOINT,
        {"query": VARIANT_QUERY, "variables": {"variantId": clean_variant_id or None, "rsid": clean_rsid or None, "dataset": dataset}},
        timeout=60,
    )
    if data.get("errors"):
        message = "; ".join(error.get("message", "unknown error") for error in data["errors"])
        if "not found" in message.lower():
            return {"query": clean_variant_id or clean_rsid, "dataset": dataset, "found": False}
        raise ValueError(message)

    record = (data.get("data") or {}).get("variant")
    if not isinstance(record, dict):
        return {"query": clean_variant_id or clean_rsid, "dataset": dataset, "found": False}

    consequences = record.get("sortedTranscriptConsequences") or []
    return {
        "query": clean_variant_id or clean_rsid,
        "dataset": dataset,
        "found": True,
        "variant_id": record.get("variantId"),
        "reference_genome": record.get("reference_genome"),
        "exome": record.get("exome") or {},
        "genome": record.get("genome") or {},
        "transcript_consequences": [
            {
                "gene_symbol": consequence.get("gene_symbol"),
                "major_consequence": consequence.get("major_consequence"),
                "transcript_id": consequence.get("transcript_id"),
                "hgvs": consequence.get("hgvs"),
            }
            for consequence in consequences[:10]
        ],
    }


FETCH_VARIANT_SPEC = ToolSpec(
    name="gnomad.fetch_variant",
    description="Fetch gnomAD variant frequency and transcript consequence summary by variantId or rsID.",
    input_schema={
        "type": "object",
        "properties": {
            "variant_id": {"type": "string"},
            "rsid": {"type": "string"},
            "dataset": {"type": "string", "default": "gnomad_r4"},
        },
    },
    output_schema={"type": "object"},
    handler=fetch_variant,
)
