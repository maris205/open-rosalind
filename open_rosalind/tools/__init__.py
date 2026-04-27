from .base import ToolSpec
from . import sequence, uniprot, pubmed, mutation

REGISTRY: dict[str, ToolSpec] = {
    sequence.ANALYZE_SPEC.name: sequence.ANALYZE_SPEC,
    uniprot.SEARCH_SPEC.name: uniprot.SEARCH_SPEC,
    uniprot.FETCH_SPEC.name: uniprot.FETCH_SPEC,
    pubmed.SEARCH_SPEC.name: pubmed.SEARCH_SPEC,
    mutation.DIFF_SPEC.name: mutation.DIFF_SPEC,
}

__all__ = ["ToolSpec", "REGISTRY"]
