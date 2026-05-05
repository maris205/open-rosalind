from open_rosalind.skills_v2 import SKILLS_V2
from open_rosalind.skills_v2.executor import execute_skill_v2
from open_rosalind.skills_v2.runtime import NullTrace
from open_rosalind.skills_v2.literature import tools as literature_tools
from open_rosalind.skills_v2.sequence import tools as seq_tools


def test_skills_v2_registry_shape():
    assert {
        "sequence_basic_analysis",
        "uniprot_lookup",
        "literature_search",
        "mutation_effect",
        "protein_annotation_summary",
        "pubmed_metadata",
        "pubmed_abstract",
        "workflow_protein_annotation",
        "workflow_mutation_assessment",
        "sequence_align_pairwise",
        "sequence_kmer_stats",
        "protein_basic_stats",
        "protein_molecular_weight",
        "uniprot_fetch_entry",
        "pubmed_search",
        "mutation_classify_basic",
        "protein_structure_summary",
        "clinvar_search",
        "literature_topic_summary",
        "mutation_impact_summary",
        "reactome_pathway_lookup",
        "go_term_lookup",
        "ensembl_gene_lookup",
        "ncbi_gene_lookup",
        "gene_cross_reference",
        "sequence_gc_content",
        "sequence_translate",
        "sequence_reverse_complement",
        "sequence_type_detect",
        "gene_literature_summary",
        "gene_pathway_summary",
        "gene_go_summary",
        "go_pathway_bridge",
        "pathway_literature_summary",
        "mutation_gene_context",
        "mutation_pathogenicity_workflow",
        "protein_structure_annotation_workflow",
    }.issubset(set(SKILLS_V2))


def test_skills_v2_metadata_examples_are_lists():
    for skill in SKILLS_V2.values():
        full = skill.to_full()
        assert full["name"]
        assert isinstance(full["examples"], list)
        assert full["input_schema"]
        assert full["output_schema"] is not None


def test_sequence_helpers_detect_type():
    out = seq_tools.detect_type("ATGGCCAAATTAA")
    assert out["records"][0]["type"] == "dna"


def test_sequence_helpers_kmer_stats():
    out = seq_tools.kmer_stats("ATATAT", k=2)
    top = dict(out["records"][0]["top_kmers"])
    assert top["AT"] == 3
    assert top["TA"] == 2


def test_sequence_helpers_protein_basic_stats():
    out = seq_tools.protein_basic_stats("MVKVGVNGFGRIGRLVTRA")
    rec = out["records"][0]
    assert rec["length"] == 19
    assert "approx_molecular_weight_da" in rec


def test_sequence_helpers_align_pairwise():
    out = seq_tools.align_pairwise("ACGT", "ACCT")
    assert out["identity"] == 0.75
    assert out["alignment"]["match_line"] == "||.|"


def test_execute_skill_v2_local():
    out = execute_skill_v2("sequence_basic_analysis", {"sequence": "ATGGCCAAATTAA"})
    assert out["annotation"]["kind"] == "sequence"
    assert out["annotation"]["primary_type"] == "dna"


def test_literature_fetch_metadata_empty():
    out = literature_tools.fetch_metadata([])
    assert out["count"] == 0
    assert out["records"] == []


def test_literature_fetch_abstract_empty():
    out = literature_tools.fetch_abstract([])
    assert out["count"] == 0
    assert out["records"] == []


def test_pubmed_metadata_skill_missing_pmids():
    out = execute_skill_v2("pubmed_metadata", {})
    assert out["annotation"]["kind"] == "literature_metadata"
    assert out["confidence"] == 0.0


def test_pubmed_abstract_skill_missing_pmids():
    out = execute_skill_v2("pubmed_abstract", {})
    assert out["annotation"]["kind"] == "literature_abstract"
    assert out["confidence"] == 0.0


def test_workflow_protein_annotation_non_protein_short_circuit():
    out = execute_skill_v2("workflow_protein_annotation", {"sequence": "ATGGCCAAATTAA"})
    assert out["annotation"]["kind"] == "workflow"
    assert out["annotation"]["workflow"] == "protein_annotation"
    assert out["annotation"]["primary_type"] == "dna"
    assert len(out["evidence"]) == 1


def test_sequence_alignment_skill_missing_inputs():
    out = execute_skill_v2("sequence_align_pairwise", {"sequence_a": "ACGT"})
    assert out["annotation"]["kind"] == "sequence_alignment"
    assert out["confidence"] == 0.0


def test_sequence_alignment_skill_success():
    out = execute_skill_v2("sequence_align_pairwise", {"sequence_a": "ACGT", "sequence_b": "ACCT"})
    assert out["annotation"]["kind"] == "sequence_alignment"
    assert out["annotation"]["identity"] == 0.75


def test_sequence_kmer_stats_skill_success():
    out = execute_skill_v2("sequence_kmer_stats", {"sequence": "ATATAT", "k": 2})
    assert out["annotation"]["kind"] == "sequence_kmer"
    assert out["annotation"]["k"] == 2
    top = dict(out["kmer_stats"]["records"][0]["top_kmers"])
    assert top["AT"] == 3


def test_sequence_gc_content_skill_success():
    out = execute_skill_v2("sequence_gc_content", {"sequence": "GCGCGCATAT"})
    assert out["annotation"]["kind"] == "sequence_gc_content"
    assert out["annotation"]["gc_percent"] == 60.0


def test_sequence_translate_skill_success():
    out = execute_skill_v2("sequence_translate", {"sequence": "ATGGCCAAATTAA"})
    assert out["annotation"]["kind"] == "sequence_translation"
    assert out["annotation"]["translation_preview"].startswith("MAK")


def test_sequence_reverse_complement_skill_success():
    out = execute_skill_v2("sequence_reverse_complement", {"sequence": "ATGCGTACGTAA"})
    assert out["annotation"]["kind"] == "sequence_reverse_complement"
    assert out["annotation"]["reverse_complement_preview"].startswith("TTACGT")


def test_sequence_type_detect_skill_success():
    out = execute_skill_v2("sequence_type_detect", {"sequence": "ATGGCCAAATTAA"})
    assert out["annotation"]["kind"] == "sequence_type"
    assert out["annotation"]["primary_type"] == "dna"


def test_protein_basic_stats_skill_success():
    out = execute_skill_v2("protein_basic_stats", {"sequence": "MVKVGVNGFGRIGRLVTRA"})
    assert out["annotation"]["kind"] == "protein_basic_stats"
    assert out["annotation"]["length"] == 19
    assert out["protein_stats"]["records"][0]["approx_molecular_weight_da"] > 0


def test_protein_molecular_weight_skill_success():
    out = execute_skill_v2("protein_molecular_weight", {"sequence": "MVKVGVNGFGRIGRLVTRA"})
    assert out["annotation"]["kind"] == "protein_molecular_weight"
    assert out["annotation"]["approx_molecular_weight_da"] > 0
    assert out["molecular_weight"]["records"][0]["length"] == 19


def test_uniprot_fetch_entry_skill_missing_accession():
    out = execute_skill_v2("uniprot_fetch_entry", {})
    assert out["annotation"]["kind"] == "protein"
    assert out["confidence"] == 0.0


def test_pubmed_search_skill_missing_query():
    out = execute_skill_v2("pubmed_search", {})
    assert out["annotation"]["kind"] == "literature"
    assert out["confidence"] == 0.0


def test_mutation_classify_basic_skill_missing_inputs():
    out = execute_skill_v2("mutation_classify_basic", {})
    assert out["annotation"]["kind"] == "mutation_classification"
    assert out["confidence"] == 0.0


def test_mutation_classify_basic_skill_success():
    out = execute_skill_v2("mutation_classify_basic", {"wild_type": "MRAAA", "mutation": "p.R2H"})
    assert out["annotation"]["kind"] == "mutation_classification"
    assert out["annotation"]["categories"] == ["missense"]
    assert out["classification"]["n_differences"] == 1


def test_protein_structure_summary_skill_missing_inputs():
    out = execute_skill_v2("protein_structure_summary", {})
    assert out["annotation"]["kind"] == "protein_structure"
    assert out["confidence"] == 0.0


def test_protein_structure_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.protein_structure_summary import handler as structure_handler_module

    monkeypatch.setattr(
        structure_handler_module.uniprot_tools,
        "fetch",
        lambda accession: {
            "accession": accession,
            "id": "P53_HUMAN",
            "name": "Cellular tumor antigen p53",
            "organism": "Homo sapiens",
            "length": 393,
        },
    )
    monkeypatch.setattr(
        structure_handler_module.alphafold_tools,
        "fetch_prediction",
        lambda accession: {
            "accession": accession,
            "count": 2,
            "models": [
                {
                    "entry_id": "AF-P04637-F1",
                    "uniprot_accession": accession,
                    "mean_plddt": 75.06,
                    "sequence_length": 393,
                    "is_reviewed": True,
                    "is_reference_proteome": True,
                    "fractions": {"very_high": 0.527},
                    "pdb_url": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.pdb",
                },
                {
                    "entry_id": "AF-P04637-9-F1",
                    "uniprot_accession": "P04637-9",
                    "mean_plddt": 82.94,
                    "sequence_length": 214,
                    "is_reviewed": True,
                    "is_reference_proteome": True,
                    "fractions": {"very_high": 0.715},
                    "pdb_url": "https://alphafold.ebi.ac.uk/files/AF-P04637-9-F1-model_v6.pdb",
                },
            ],
        },
    )

    out = execute_skill_v2("protein_structure_summary", {"accession": "P04637"})
    assert out["annotation"]["kind"] == "protein_structure"
    assert out["annotation"]["model_id"] == "AF-P04637-F1"
    assert out["annotation"]["n_models"] == 2
    assert out["structure"]["primary_model"]["entry_id"] == "AF-P04637-F1"


def test_clinvar_search_skill_missing_inputs():
    out = execute_skill_v2("clinvar_search", {})
    assert out["annotation"]["kind"] == "clinvar"
    assert out["confidence"] == 0.0


def test_clinvar_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.clinvar_search import handler as clinvar_handler_module

    monkeypatch.setattr(
        clinvar_handler_module.clinvar_tools,
        "search",
        lambda query, max_results=5: {
            "query": query,
            "count": 1,
            "records": [
                {
                    "uid": "12374",
                    "accession": "VCV000012374",
                    "gene": "TP53",
                    "protein_change": "R175H",
                    "trait_names": ["Li-Fraumeni syndrome"],
                    "germline_classification": {"description": "Pathogenic"},
                    "oncogenicity_classification": {"description": "Oncogenic"},
                    "clinical_impact_classification": {"description": "Tier I - Strong"},
                }
            ],
        },
    )

    out = execute_skill_v2("clinvar_search", {"gene_symbol": "TP53", "mutation": "R175H"})
    assert out["annotation"]["kind"] == "clinvar"
    assert out["annotation"]["germline_significance"] == "Pathogenic"
    assert out["annotation"]["oncogenicity"] == "Oncogenic"
    assert out["clinvar"]["count"] == 1
    assert any("Built ClinVar query" in note for note in out["notes"])


def test_literature_topic_summary_skill_missing_query():
    out = execute_skill_v2("literature_topic_summary", {})
    assert out["annotation"]["kind"] == "literature_topic_summary"
    assert out["confidence"] == 0.0


def test_literature_topic_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.literature_topic_summary import handler as topic_handler_module

    monkeypatch.setattr(
        topic_handler_module.tools,
        "search",
        lambda query, max_results=5: {
            "query": query,
            "count": 2,
            "hits": [
                {"pmid": "12345", "title": "CRISPR base editing improves precision"},
                {"pmid": "67890", "title": "Base editing delivery strategies"},
            ],
        },
    )
    monkeypatch.setattr(
        topic_handler_module.tools,
        "fetch_metadata",
        lambda pmids: {
            "count": 2,
            "records": [
                {
                    "pmid": "12345",
                    "title": "CRISPR base editing improves precision",
                    "journal": "Nature Biotechnology",
                    "year": "2024",
                    "doi": "10.1038/example1",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
                },
                {
                    "pmid": "67890",
                    "title": "Base editing delivery strategies",
                    "journal": "Nature Methods",
                    "year": "2023",
                    "doi": "10.1038/example2",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/67890/",
                },
            ],
        },
    )
    monkeypatch.setattr(
        topic_handler_module.tools,
        "fetch_abstract",
        lambda pmids: {
            "count": 2,
            "records": [
                {
                    "pmid": "12345",
                    "abstract": "Base editing improves precision in genome engineering and reduces bystander edits.",
                },
                {
                    "pmid": "67890",
                    "abstract": "Delivery strategies shape editing efficiency across tissues and model systems.",
                },
            ],
        },
    )

    out = execute_skill_v2("literature_topic_summary", {"query": "CRISPR base editing", "max_results": 2})
    assert out["annotation"]["kind"] == "literature_topic_summary"
    assert out["annotation"]["top_pmids"] == ["12345", "67890"]
    assert out["topic_summary"]["papers_considered"] == 2
    assert out["topic_summary"]["highlights"][0]["pmid"] == "12345"
    assert out["topic_summary"]["recurring_terms"]


def test_mutation_impact_summary_skill_missing_inputs():
    out = execute_skill_v2("mutation_impact_summary", {})
    assert out["annotation"]["kind"] == "mutation_impact_summary"
    assert out["confidence"] == 0.0


def test_mutation_impact_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2 import mutation_impact_summary as impact_pkg
    from open_rosalind.skills_v2.mutation_impact_summary import handler as impact_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "mutation_effect":
            return {
                "annotation": {
                    "kind": "mutation",
                    "gene_symbol": "TP53",
                    "accession": "P04637",
                    "overall_assessment": "likely impactful",
                    "notable_flags": ["charge reversal"],
                },
                "confidence": 0.85,
                "notes": ["Resolved gene symbol 'TP53' to UniProt P04637"],
                "mutation": {
                    "n_differences": 1,
                    "differences": [{"category": "missense", "severity": "high"}],
                },
            }
        if name == "clinvar_search":
            return {
                "annotation": {
                    "kind": "clinvar",
                    "germline_significance": "Pathogenic",
                    "oncogenicity": "Oncogenic",
                    "clinical_impact": "Tier I - Strong",
                    "trait_names": ["Li-Fraumeni syndrome"],
                },
                "confidence": 0.85,
                "notes": [],
                "clinvar": {"count": 1, "records": [{"accession": "VCV000012374"}]},
            }
        if name == "protein_annotation_summary":
            return {
                "annotation": {
                    "kind": "protein",
                    "name": "Cellular tumor antigen p53",
                    "organism": "Homo sapiens",
                    "function": "Tumor suppressor",
                },
                "confidence": 0.9,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(impact_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("mutation_impact_summary", {"gene_symbol": "TP53", "mutation": "p.R175H"})
    assert out["annotation"]["kind"] == "mutation_impact_summary"
    assert out["annotation"]["germline_significance"] == "Pathogenic"
    assert out["annotation"]["oncogenicity"] == "Oncogenic"
    assert out["impact_summary"]["overall_assessment"] == "likely impactful"
    assert [step["step"] for step in out["evidence"]] == [
        "mutation_effect",
        "clinvar_search",
        "protein_annotation_summary",
    ]


def test_reactome_pathway_lookup_skill_missing_inputs():
    out = execute_skill_v2("reactome_pathway_lookup", {})
    assert out["annotation"]["kind"] == "pathway"
    assert out["confidence"] == 0.0


def test_reactome_pathway_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.reactome_pathway_lookup import handler as pathway_handler_module

    monkeypatch.setattr(
        pathway_handler_module.reactome_tools,
        "search_pathways",
        lambda query, species="Homo sapiens", max_results=5: {
            "query": query,
            "species": species,
            "count": 1,
            "records": [
                {
                    "st_id": "R-HSA-69541",
                    "name": "Stabilization of p53",
                    "summary": "p53 stabilization pathway",
                    "species": ["Homo sapiens"],
                }
            ],
        },
    )
    monkeypatch.setattr(
        pathway_handler_module.reactome_tools,
        "fetch_pathway",
        lambda stable_id: {
            "st_id": stable_id,
            "display_name": "Stabilization of p53",
            "species": "Homo sapiens",
            "event_count": 11,
            "literature": [{"pmid": "11331603"}],
            "summary": "ATM and CHEK2 stabilize p53 after DNA damage.",
        },
    )

    out = execute_skill_v2("reactome_pathway_lookup", {"query": "TP53"})
    assert out["annotation"]["kind"] == "pathway"
    assert out["annotation"]["stable_id"] == "R-HSA-69541"
    assert out["annotation"]["event_count"] == 11
    assert out["pathway"]["display_name"] == "Stabilization of p53"
    assert any("Resolved Reactome query" in note for note in out["notes"])


def test_go_term_lookup_skill_missing_inputs():
    out = execute_skill_v2("go_term_lookup", {})
    assert out["annotation"]["kind"] == "go_term"
    assert out["confidence"] == 0.0


def test_go_term_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.go_term_lookup import handler as go_handler_module

    monkeypatch.setattr(
        go_handler_module.quickgo_tools,
        "search_terms",
        lambda query, max_results=5: {
            "query": query,
            "count": 1,
            "records": [
                {
                    "id": "GO:0006915",
                    "name": "apoptotic process",
                    "aspect": "biological_process",
                }
            ],
        },
    )
    monkeypatch.setattr(
        go_handler_module.quickgo_tools,
        "fetch_term",
        lambda term_id: {
            "id": term_id,
            "found": True,
            "name": "apoptotic process",
            "aspect": "biological_process",
            "is_obsolete": False,
            "definition": "Programmed cell death process.",
            "child_terms": [{"id": "GO:0051402", "relation": "is_a"}],
        },
    )

    out = execute_skill_v2("go_term_lookup", {"query": "apoptotic process"})
    assert out["annotation"]["kind"] == "go_term"
    assert out["annotation"]["term_id"] == "GO:0006915"
    assert out["annotation"]["n_child_terms"] == 1
    assert out["term"]["name"] == "apoptotic process"
    assert any("Resolved GO query" in note for note in out["notes"])


def test_ensembl_gene_lookup_skill_missing_inputs():
    out = execute_skill_v2("ensembl_gene_lookup", {})
    assert out["annotation"]["kind"] == "gene"
    assert out["confidence"] == 0.0


def test_ensembl_gene_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.ensembl_gene_lookup import handler as ensembl_handler_module

    monkeypatch.setattr(
        ensembl_handler_module.ensembl_tools,
        "lookup_gene",
        lambda symbol, species="homo_sapiens": {
            "query": symbol,
            "species": species,
            "found": True,
            "ensembl_gene_id": "ENSG00000141510",
            "symbol": "TP53",
            "description": "tumor protein p53",
            "biotype": "protein_coding",
            "canonical_transcript": "ENST00000269305.9",
            "n_transcripts": 19,
            "seq_region_name": "17",
            "transcripts": [{"id": "ENST00000269305.9", "is_canonical": True}],
        },
    )

    out = execute_skill_v2("ensembl_gene_lookup", {"symbol": "TP53"})
    assert out["annotation"]["kind"] == "gene"
    assert out["annotation"]["ensembl_gene_id"] == "ENSG00000141510"
    assert out["annotation"]["canonical_transcript"] == "ENST00000269305.9"
    assert out["gene"]["n_transcripts"] == 19


def test_ncbi_gene_lookup_skill_missing_inputs():
    out = execute_skill_v2("ncbi_gene_lookup", {})
    assert out["annotation"]["kind"] == "gene"
    assert out["confidence"] == 0.0


def test_ncbi_gene_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.ncbi_gene_lookup import handler as ncbi_handler_module

    monkeypatch.setattr(
        ncbi_handler_module.ncbi_gene_tools,
        "search_gene",
        lambda query, species="Homo sapiens", max_results=3: {
            "query": query,
            "species": species,
            "count": 1,
            "ids": ["7157"],
        },
    )
    monkeypatch.setattr(
        ncbi_handler_module.ncbi_gene_tools,
        "fetch_gene",
        lambda gene_id: {
            "gene_id": gene_id,
            "found": True,
            "symbol": "TP53",
            "species": "Homo sapiens",
            "chromosome": "17",
            "map_location": "17p13.1",
            "mim_ids": ["191170"],
            "aliases": ["P53", "TRP53"],
        },
    )

    out = execute_skill_v2("ncbi_gene_lookup", {"query": "TP53"})
    assert out["annotation"]["kind"] == "gene"
    assert out["annotation"]["gene_id"] == "7157"
    assert out["annotation"]["map_location"] == "17p13.1"
    assert any("Resolved NCBI query" in note for note in out["notes"])


def test_gene_cross_reference_skill_missing_inputs():
    out = execute_skill_v2("gene_cross_reference", {})
    assert out["annotation"]["kind"] == "gene_cross_reference"
    assert out["confidence"] == 0.0


def test_gene_cross_reference_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gene_cross_reference import handler as xref_handler_module

    monkeypatch.setattr(
        xref_handler_module.ensembl_tools,
        "lookup_gene",
        lambda symbol, species="homo_sapiens": {
            "query": symbol,
            "species": species,
            "found": True,
            "ensembl_gene_id": "ENSG00000141510",
            "symbol": "TP53",
            "biotype": "protein_coding",
            "canonical_transcript": "ENST00000269305.9",
            "seq_region_name": "17",
        },
    )
    monkeypatch.setattr(
        xref_handler_module.ensembl_tools,
        "fetch_xrefs",
        lambda ensembl_id: {
            "ensembl_id": ensembl_id,
            "count": 3,
            "records": [
                {"dbname": "EntrezGene", "primary_id": "7157", "display_id": "TP53"},
                {"dbname": "HGNC", "primary_id": "HGNC:11998", "display_id": "TP53"},
                {"dbname": "MIM_GENE", "primary_id": "191170", "display_id": "TP53"},
            ],
        },
    )
    monkeypatch.setattr(
        xref_handler_module.ncbi_gene_tools,
        "fetch_gene",
        lambda gene_id: {
            "gene_id": gene_id,
            "found": True,
            "symbol": "TP53",
            "species": "Homo sapiens",
            "chromosome": "17",
            "map_location": "17p13.1",
            "aliases": ["P53", "TRP53"],
            "mim_ids": ["191170"],
        },
    )

    out = execute_skill_v2("gene_cross_reference", {"query": "TP53"})
    assert out["annotation"]["kind"] == "gene_cross_reference"
    assert out["annotation"]["ensembl_gene_id"] == "ENSG00000141510"
    assert out["annotation"]["ncbi_gene_id"] == "7157"
    assert out["cross_references"]["hgnc_ids"] == ["HGNC:11998"]
    assert out["cross_references"]["omim_ids"] == ["191170"]
    assert any("Resolved NCBI Gene ID 7157 from Ensembl cross-references" in note for note in out["notes"])


def test_gene_literature_summary_skill_missing_inputs():
    out = execute_skill_v2("gene_literature_summary", {})
    assert out["annotation"]["kind"] == "gene_literature_summary"
    assert out["confidence"] == 0.0


def test_gene_literature_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gene_literature_summary import handler as gls_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "gene_cross_reference":
            return {
                "annotation": {
                    "kind": "gene_cross_reference",
                    "symbol": "TP53",
                    "species": "Homo sapiens",
                    "ensembl_gene_id": "ENSG00000141510",
                    "ncbi_gene_id": "7157",
                    "canonical_transcript": "ENST00000269305.9",
                    "omim_ids": ["191170"],
                },
                "confidence": 0.91,
                "notes": [],
            }
        if name == "literature_topic_summary":
            return {
                "annotation": {
                    "kind": "literature_topic_summary",
                    "n_hits": 2,
                    "top_pmids": ["12345", "67890"],
                },
                "confidence": 0.85,
                "notes": [],
                "topic_summary": {"papers_considered": 2},
            }
        raise AssertionError(name)

    monkeypatch.setattr(gls_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("gene_literature_summary", {"query": "TP53"})
    assert out["annotation"]["kind"] == "gene_literature_summary"
    assert out["annotation"]["ensembl_gene_id"] == "ENSG00000141510"
    assert out["annotation"]["top_pmids"] == ["12345", "67890"]
    assert [step["step"] for step in out["evidence"]] == [
        "gene_cross_reference",
        "literature_topic_summary",
    ]


def test_gene_pathway_summary_skill_missing_inputs():
    out = execute_skill_v2("gene_pathway_summary", {})
    assert out["annotation"]["kind"] == "gene_pathway_summary"
    assert out["confidence"] == 0.0


def test_gene_pathway_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gene_pathway_summary import handler as gps_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "gene_cross_reference":
            return {
                "annotation": {
                    "kind": "gene_cross_reference",
                    "symbol": "TP53",
                    "species": "Homo sapiens",
                    "ensembl_gene_id": "ENSG00000141510",
                    "ncbi_gene_id": "7157",
                },
                "confidence": 0.91,
                "notes": [],
            }
        if name == "reactome_pathway_lookup":
            return {
                "annotation": {
                    "kind": "pathway",
                    "stable_id": "R-HSA-69541",
                    "name": "Stabilization of p53",
                    "event_count": 11,
                    "literature_count": 1,
                },
                "confidence": 0.85,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(gps_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("gene_pathway_summary", {"query": "TP53"})
    assert out["annotation"]["kind"] == "gene_pathway_summary"
    assert out["annotation"]["pathway_stable_id"] == "R-HSA-69541"
    assert out["annotation"]["event_count"] == 11
    assert [step["step"] for step in out["evidence"]] == [
        "gene_cross_reference",
        "reactome_pathway_lookup",
    ]


def test_protein_structure_annotation_workflow_missing_inputs():
    out = execute_skill_v2("protein_structure_annotation_workflow", {})
    assert out["annotation"]["kind"] == "workflow"
    assert out["confidence"] == 0.0


def test_protein_structure_annotation_workflow_success(monkeypatch):
    from open_rosalind.skills_v2.protein_structure_annotation_workflow import handler as psaw_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "protein_annotation_summary":
            return {
                "annotation": {
                    "kind": "protein",
                    "accession": "P04637",
                    "name": "Cellular tumor antigen p53",
                    "organism": "Homo sapiens",
                    "length": 393,
                },
                "confidence": 0.9,
                "notes": [],
            }
        if name == "protein_structure_summary":
            return {
                "annotation": {
                    "kind": "protein_structure",
                    "accession": "P04637",
                    "name": "Cellular tumor antigen p53",
                    "organism": "Homo sapiens",
                    "length": 393,
                    "model_id": "AF-P04637-F1",
                    "mean_plddt": 75.06,
                    "n_models": 2,
                },
                "confidence": 0.75,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(psaw_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("protein_structure_annotation_workflow", {"accession": "P04637"})
    assert out["annotation"]["kind"] == "workflow"
    assert out["annotation"]["workflow"] == "protein_structure_annotation"
    assert out["annotation"]["model_id"] == "AF-P04637-F1"
    assert [step["step"] for step in out["evidence"]] == [
        "protein_annotation_summary",
        "protein_structure_summary",
    ]


def test_gene_go_summary_skill_missing_inputs():
    out = execute_skill_v2("gene_go_summary", {})
    assert out["annotation"]["kind"] == "gene_go_summary"
    assert out["confidence"] == 0.0


def test_gene_go_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gene_go_summary import handler as ggs_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "gene_cross_reference":
            return {
                "annotation": {
                    "kind": "gene_cross_reference",
                    "symbol": "TP53",
                    "species": "Homo sapiens",
                    "ensembl_gene_id": "ENSG00000141510",
                    "ncbi_gene_id": "7157",
                },
                "confidence": 0.91,
                "notes": [],
            }
        if name == "go_term_lookup":
            return {
                "annotation": {
                    "kind": "go_term",
                    "term_id": "GO:0006915",
                    "name": "apoptotic process",
                    "aspect": "biological_process",
                    "n_child_terms": 1,
                },
                "confidence": 0.85,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(ggs_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("gene_go_summary", {"query": "TP53"})
    assert out["annotation"]["kind"] == "gene_go_summary"
    assert out["annotation"]["term_id"] == "GO:0006915"
    assert out["annotation"]["term_name"] == "apoptotic process"
    assert [step["step"] for step in out["evidence"]] == [
        "gene_cross_reference",
        "go_term_lookup",
    ]


def test_go_pathway_bridge_skill_missing_inputs():
    out = execute_skill_v2("go_pathway_bridge", {})
    assert out["annotation"]["kind"] == "go_pathway_bridge"
    assert out["confidence"] == 0.0


def test_go_pathway_bridge_skill_success(monkeypatch):
    from open_rosalind.skills_v2.go_pathway_bridge import handler as gpb_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "go_term_lookup":
            return {
                "annotation": {
                    "kind": "go_term",
                    "term_id": "GO:0006915",
                    "name": "apoptotic process",
                    "aspect": "biological_process",
                },
                "confidence": 0.85,
                "notes": [],
            }
        if name == "reactome_pathway_lookup":
            return {
                "annotation": {
                    "kind": "pathway",
                    "stable_id": "R-HSA-109581",
                    "name": "Apoptosis",
                    "event_count": 18,
                },
                "confidence": 0.85,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(gpb_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("go_pathway_bridge", {"query": "apoptotic process"})
    assert out["annotation"]["kind"] == "go_pathway_bridge"
    assert out["annotation"]["pathway_stable_id"] == "R-HSA-109581"
    assert out["annotation"]["event_count"] == 18
    assert [step["step"] for step in out["evidence"]] == [
        "go_term_lookup",
        "reactome_pathway_lookup",
    ]


def test_pathway_literature_summary_skill_missing_inputs():
    out = execute_skill_v2("pathway_literature_summary", {})
    assert out["annotation"]["kind"] == "pathway_literature_summary"
    assert out["confidence"] == 0.0


def test_pathway_literature_summary_skill_success(monkeypatch):
    from open_rosalind.skills_v2.pathway_literature_summary import handler as pls_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "reactome_pathway_lookup":
            return {
                "annotation": {
                    "kind": "pathway",
                    "stable_id": "R-HSA-109581",
                    "name": "Apoptosis",
                    "species": "Homo sapiens",
                    "event_count": 18,
                },
                "confidence": 0.85,
                "notes": [],
            }
        if name == "literature_topic_summary":
            return {
                "annotation": {
                    "kind": "literature_topic_summary",
                    "n_hits": 2,
                    "top_pmids": ["11111", "22222"],
                },
                "confidence": 0.85,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(pls_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("pathway_literature_summary", {"query": "TP53"})
    assert out["annotation"]["kind"] == "pathway_literature_summary"
    assert out["annotation"]["stable_id"] == "R-HSA-109581"
    assert out["annotation"]["top_pmids"] == ["11111", "22222"]
    assert [step["step"] for step in out["evidence"]] == [
        "reactome_pathway_lookup",
        "literature_topic_summary",
    ]


def test_mutation_gene_context_skill_missing_inputs():
    out = execute_skill_v2("mutation_gene_context", {})
    assert out["annotation"]["kind"] == "mutation_gene_context"
    assert out["confidence"] == 0.0


def test_mutation_gene_context_skill_success(monkeypatch):
    from open_rosalind.skills_v2.mutation_gene_context import handler as mgc_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "mutation_effect":
            return {
                "annotation": {
                    "kind": "mutation",
                    "gene_symbol": "TP53",
                    "accession": "P04637",
                    "overall_assessment": "likely impactful",
                    "n_differences": 1,
                },
                "confidence": 0.85,
                "notes": [],
                "protein_context": {"accession": "P04637"},
            }
        if name == "gene_cross_reference":
            return {
                "annotation": {
                    "kind": "gene_cross_reference",
                    "symbol": "TP53",
                    "ensembl_gene_id": "ENSG00000141510",
                    "ncbi_gene_id": "7157",
                    "canonical_transcript": "ENST00000269305.9",
                },
                "confidence": 0.91,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(mgc_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("mutation_gene_context", {"gene_symbol": "TP53", "mutation": "p.R175H"})
    assert out["annotation"]["kind"] == "mutation_gene_context"
    assert out["annotation"]["ensembl_gene_id"] == "ENSG00000141510"
    assert out["annotation"]["overall_assessment"] == "likely impactful"
    assert [step["step"] for step in out["evidence"]] == [
        "mutation_effect",
        "gene_cross_reference",
    ]


def test_mutation_pathogenicity_workflow_missing_inputs():
    out = execute_skill_v2("mutation_pathogenicity_workflow", {})
    assert out["annotation"]["kind"] == "workflow"
    assert out["confidence"] == 0.0


def test_mutation_pathogenicity_workflow_success(monkeypatch):
    from open_rosalind.skills_v2.mutation_pathogenicity_workflow import handler as mpw_handler_module

    def fake_execute(name, payload, trace=None):
        if name == "mutation_impact_summary":
            return {
                "annotation": {
                    "kind": "mutation_impact_summary",
                    "gene_symbol": "TP53",
                    "accession": "P04637",
                    "protein_name": "Cellular tumor antigen p53",
                    "mutation": "p.R175H",
                    "overall_assessment": "likely impactful",
                    "germline_significance": "Pathogenic",
                    "oncogenicity": "Oncogenic",
                },
                "confidence": 0.86,
                "notes": [],
            }
        if name == "literature_topic_summary":
            return {
                "annotation": {
                    "kind": "literature_topic_summary",
                    "n_hits": 2,
                    "top_pmids": ["12345", "67890"],
                },
                "confidence": 0.85,
                "notes": [],
            }
        raise AssertionError(name)

    monkeypatch.setattr(mpw_handler_module, "execute_skill_v2", fake_execute)

    out = execute_skill_v2("mutation_pathogenicity_workflow", {"gene_symbol": "TP53", "mutation": "p.R175H"})
    assert out["annotation"]["kind"] == "workflow"
    assert out["annotation"]["workflow"] == "mutation_pathogenicity"
    assert out["annotation"]["germline_significance"] == "Pathogenic"
    assert out["annotation"]["top_pmids"] == ["12345", "67890"]
    assert [step["step"] for step in out["evidence"]] == [
        "mutation_impact_summary",
        "literature_topic_summary",
    ]


def test_uniprot_skill_cleans_query_and_uses_gene_fallback(monkeypatch):
    from open_rosalind.skills_v2.uniprot import tools as uniprot_tools

    seen_queries = []

    def fake_search(query: str, max_results: int = 10) -> dict:
        seen_queries.append(query)
        if query == "TP53":
            return {"count": 0, "hits": []}
        if query == 'gene_exact:TP53 AND organism_name:"Homo sapiens"':
            return {
                "count": 1,
                "hits": [
                    {
                        "accession": "P04637",
                        "name": "Cellular tumor antigen p53",
                        "organism": "Homo sapiens",
                    }
                ],
            }
        raise AssertionError(f"unexpected query: {query}")

    def fake_fetch(accession: str) -> dict:
        assert accession == "P04637"
        return {
            "accession": "P04637",
            "id": "P53_HUMAN",
            "name": "Cellular tumor antigen p53",
            "organism": "Homo sapiens",
            "sequence": "MEEPQ",
        }

    monkeypatch.setattr(uniprot_tools, "search", fake_search)
    monkeypatch.setattr(uniprot_tools, "fetch", fake_fetch)

    out = execute_skill_v2("uniprot_lookup", {"query": "What is the molecular function of TP53 in humans?"})
    assert out["annotation"]["accession"] == "P04637"
    assert out["annotation"]["organism"] == "Homo sapiens"
    assert out["entry"]["id"] == "P53_HUMAN"
    assert any("gene-specific search fallback" in note for note in out["notes"])
    assert seen_queries == ["TP53", 'gene_exact:TP53 AND organism_name:"Homo sapiens"']


def test_uniprot_skill_accession_path_still_searches(monkeypatch):
    from open_rosalind.skills_v2.uniprot import tools as uniprot_tools

    trace = NullTrace()

    monkeypatch.setattr(
        uniprot_tools,
        "fetch",
        lambda accession: {
            "accession": accession,
            "id": "BRCA1_HUMAN",
            "name": "Breast cancer type 1 susceptibility protein",
            "organism": "Homo sapiens",
            "sequence": "M" * 10,
        },
    )
    monkeypatch.setattr(
        uniprot_tools,
        "search",
        lambda query, max_results=10: {
            "count": 1,
            "hits": [{"accession": "P38398", "name": "Breast cancer type 1 susceptibility protein", "organism": "Homo sapiens"}],
        },
    )

    out = execute_skill_v2("uniprot_lookup", {"query": "P38398", "accession": "P38398"}, trace=trace)
    assert out["entry"]["id"] == "BRCA1_HUMAN"
    tool_calls = [event["tool"] for event in trace.events if event.get("kind") == "tool_call"]
    assert tool_calls == ["uniprot.fetch", "uniprot.search"]


def test_uniprot_fetch_entry_skill_success(monkeypatch):
    from open_rosalind.skills_v2.uniprot_fetch_entry import handler as fetch_handler_module

    monkeypatch.setattr(
        fetch_handler_module.tools,
        "fetch",
        lambda accession: {
            "accession": accession,
            "id": "BRCA1_HUMAN",
            "name": "Breast cancer type 1 susceptibility protein",
            "organism": "Homo sapiens",
            "length": 1863,
            "sequence": "M" * 20,
        },
    )

    out = execute_skill_v2("uniprot_fetch_entry", {"accession": "P38398"})
    assert out["annotation"]["accession"] == "P38398"
    assert out["entry"]["id"] == "BRCA1_HUMAN"


def test_literature_skill_cleans_query_and_drops_year_filter(monkeypatch):
    calls = []

    def fake_search(query: str, max_results: int = 10) -> dict:
        calls.append(query)
        if query == "(long-read sequencing) AND 2024[dp]":
            return {"query": query, "count": 0, "hits": []}
        if query == "long-read sequencing":
            return {"query": query, "count": 1, "hits": [{"pmid": "111", "title": "Long-read paper"}]}
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr(literature_tools, "search", fake_search)
    monkeypatch.setattr(
        literature_tools,
        "fetch_metadata",
        lambda pmids: {"count": 1, "records": [{"pmid": "111", "title": "Long-read paper"}]},
    )
    monkeypatch.setattr(
        literature_tools,
        "fetch_abstract",
        lambda pmids: {"count": 1, "records": [{"pmid": "111", "abstract": "abstract"}]},
    )

    out = execute_skill_v2("literature_search", {"query": "Find recent papers about long-read sequencing in 2024"})
    assert out["annotation"]["query"] == "(long-read sequencing) AND 2024[dp]"
    assert out["pubmed"]["count"] == 1
    assert out["metadata"]["count"] == 1
    assert any("Relaxed year-constrained query" in note for note in out["notes"])
    assert calls == ["(long-read sequencing) AND 2024[dp]", "long-read sequencing"]


def test_pubmed_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.pubmed_search import handler as pubmed_search_handler_module

    monkeypatch.setattr(
        pubmed_search_handler_module.tools,
        "search",
        lambda query, max_results=10: {
            "query": query,
            "count": 1,
            "hits": [{"pmid": "12345", "title": "CRISPR base editing"}],
        },
    )

    out = execute_skill_v2("pubmed_search", {"query": "CRISPR base editing", "max_results": 5})
    assert out["annotation"]["kind"] == "literature"
    assert out["annotation"]["top_pmids"] == ["12345"]
    assert out["pubmed"]["count"] == 1


def test_mutation_skill_resolves_gene_symbol(monkeypatch):
    from open_rosalind.skills_v2.uniprot import tools as uniprot_tools

    def fake_search(query: str, max_results: int = 10) -> dict:
        assert query == "TP53"
        assert max_results == 5
        return {
            "count": 1,
            "hits": [
                {
                    "accession": "P04637",
                    "name": "P53_HUMAN",
                    "organism": "Homo sapiens",
                }
            ],
        }

    def fake_fetch(accession: str) -> dict:
        assert accession == "P04637"
        return {
            "accession": accession,
            "name": "P53_HUMAN",
            "organism": "Homo sapiens",
            "sequence": "MRAAA",
        }

    monkeypatch.setattr(uniprot_tools, "search", fake_search)
    monkeypatch.setattr(uniprot_tools, "fetch", fake_fetch)

    out = execute_skill_v2("mutation_effect", {"gene_symbol": "TP53", "mutation": "p.R2H"})
    assert out["annotation"]["kind"] == "mutation"
    assert out["annotation"]["accession"] == "P04637"
    assert out["mutation"]["n_differences"] == 1
    assert out["mutation"]["differences"][0]["position"] == 2
    assert "Resolved gene symbol" in out["notes"][0]


def test_workflow_mutation_assessment_aggregates_evidence(monkeypatch):
    from open_rosalind.skills_v2.literature import tools as literature_tools
    from open_rosalind.skills_v2.uniprot import tools as uniprot_tools

    def fake_search(query: str, max_results: int = 10) -> dict:
        if query == "TP53":
            assert max_results == 5
            return {
                "count": 1,
                "hits": [
                    {
                        "accession": "P04637",
                        "name": "P53_HUMAN",
                        "organism": "Homo sapiens",
                    }
                ],
            }
        assert query == "TP53 R2H"
        assert max_results == 10
        return {
            "count": 1,
            "query": query,
            "hits": [{"pmid": "12345", "title": "TP53 R2H study"}],
        }

    def fake_fetch(accession: str) -> dict:
        assert accession == "P04637"
        return {
            "accession": accession,
            "name": "P53_HUMAN",
            "organism": "Homo sapiens",
            "function": "Tumor suppressor",
            "length": 5,
            "sequence": "MRAAA",
        }

    monkeypatch.setattr(uniprot_tools, "search", fake_search)
    monkeypatch.setattr(uniprot_tools, "fetch", fake_fetch)
    monkeypatch.setattr(literature_tools, "search", fake_search)
    monkeypatch.setattr(
        literature_tools,
        "fetch_metadata",
        lambda pmids: {"count": 1, "records": [{"pmid": "12345", "title": "TP53 R2H study"}]},
    )
    monkeypatch.setattr(
        literature_tools,
        "fetch_abstract",
        lambda pmids: {"count": 1, "records": [{"pmid": "12345", "abstract": "Rule-based benchmark abstract."}]},
    )

    out = execute_skill_v2(
        "workflow_mutation_assessment",
        {"gene_symbol": "TP53", "mutation": "p.R2H", "query": "What is known about TP53 R2H?"},
    )
    assert out["annotation"]["kind"] == "workflow"
    assert out["annotation"]["workflow"] == "mutation_assessment"
    assert out["annotation"]["accession"] == "P04637"
    assert out["annotation"]["n_differences"] == 1
    assert [step["step"] for step in out["evidence"]] == [
        "mutation_effect",
        "protein_annotation_summary",
        "literature_search",
    ]
    assert out["protein_result"]["annotation"]["name"] == "P53_HUMAN"
    assert out["literature_result"]["annotation"]["top_pmids"] == ["12345"]
    tool_names = [event["tool"] for event in out["trace"] if event.get("kind") == "tool_call"]
    assert "mutation.diff" in tool_names
    assert "pubmed.search" in tool_names
