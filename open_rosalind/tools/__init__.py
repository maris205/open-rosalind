from .base import ToolSpec
from . import alphafold, clinvar, ensembl, mutation, ncbi_gene, pubmed, quickgo, reactome, sequence, uniprot

REGISTRY: dict[str, ToolSpec] = {
    sequence.ANALYZE_SPEC.name: sequence.ANALYZE_SPEC,
    sequence.ALIGN_PAIRWISE_SPEC.name: sequence.ALIGN_PAIRWISE_SPEC,
    uniprot.SEARCH_SPEC.name: uniprot.SEARCH_SPEC,
    uniprot.FETCH_SPEC.name: uniprot.FETCH_SPEC,
    pubmed.SEARCH_SPEC.name: pubmed.SEARCH_SPEC,
    pubmed.FETCH_METADATA_SPEC.name: pubmed.FETCH_METADATA_SPEC,
    pubmed.FETCH_ABSTRACT_SPEC.name: pubmed.FETCH_ABSTRACT_SPEC,
    mutation.DIFF_SPEC.name: mutation.DIFF_SPEC,
    alphafold.FETCH_PREDICTION_SPEC.name: alphafold.FETCH_PREDICTION_SPEC,
    clinvar.SEARCH_SPEC.name: clinvar.SEARCH_SPEC,
    reactome.SEARCH_PATHWAYS_SPEC.name: reactome.SEARCH_PATHWAYS_SPEC,
    reactome.FETCH_PATHWAY_SPEC.name: reactome.FETCH_PATHWAY_SPEC,
    quickgo.SEARCH_TERMS_SPEC.name: quickgo.SEARCH_TERMS_SPEC,
    quickgo.FETCH_TERM_SPEC.name: quickgo.FETCH_TERM_SPEC,
    ensembl.LOOKUP_GENE_SPEC.name: ensembl.LOOKUP_GENE_SPEC,
    ensembl.FETCH_XREFS_SPEC.name: ensembl.FETCH_XREFS_SPEC,
    ncbi_gene.SEARCH_GENE_SPEC.name: ncbi_gene.SEARCH_GENE_SPEC,
    ncbi_gene.FETCH_GENE_SPEC.name: ncbi_gene.FETCH_GENE_SPEC,
}

__all__ = ["ToolSpec", "REGISTRY"]
