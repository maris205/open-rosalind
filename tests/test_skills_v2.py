import json

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
        "clinicaltrials_search",
        "string_network",
        "chembl_search",
        "clinvar_variation_lookup",
        "gnomad_variant_lookup",
        "gwas_catalog_search",
        "opentargets_target_disease",
        "civic_variant_evidence",
        "bgee_expression_lookup",
        "human_protein_atlas_lookup",
        "rcsb_pdb_lookup",
        "pharmgkb_clinical_annotation",
        "ncbi_blast_search",
        "efo_term_lookup",
        "pubchem_compound_lookup",
        "chebi_compound_lookup",
        "bindingdb_target_ligands",
        "cellxgene_collection_lookup",
        "pride_project_lookup",
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


def test_clinicaltrials_search_studies_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import clinicaltrials as clinicaltrials_tools

    class FakeResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, data):
            self.data = data
            self.requests = []

        def get(self, url, params=None, headers=None, timeout=None):
            self.requests.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
            return FakeResponse(self.data)

        def close(self):
            return None

    fake_session = FakeSession(
        {
            "totalCount": 1,
            "studies": [
                {
                    "protocolSection": {
                        "identificationModule": {
                            "nctId": "NCT01234567",
                            "briefTitle": "Trial of TP53 inhibitor",
                            "officialTitle": "A Phase 2 Study of a TP53 Inhibitor",
                        },
                        "statusModule": {
                            "overallStatus": "RECRUITING",
                            "startDateStruct": {"date": "2025-01-01"},
                            "primaryCompletionDateStruct": {"date": "2026-06-01"},
                        },
                        "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE2"]},
                        "conditionsModule": {"conditions": ["Glioblastoma"]},
                        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Open Rosalind Hospital"}},
                        "contactsLocationsModule": {
                            "locations": [
                                {
                                    "facility": "Main Hospital",
                                    "city": "Seattle",
                                    "state": "WA",
                                    "country": "United States",
                                }
                            ]
                        },
                    }
                }
            ],
        }
    )
    monkeypatch.setattr(clinicaltrials_tools, "make_session", lambda: fake_session)

    out = clinicaltrials_tools.search_studies("glioblastoma", status="recruiting", max_results=1)
    assert out["count"] == 1
    assert out["records"][0]["nct_id"] == "NCT01234567"
    assert out["records"][0]["overall_status"] == "RECRUITING"
    assert out["records"][0]["locations"][0]["summary"] == "Main Hospital, Seattle, WA, United States"


def test_string_interaction_partners_tool_parses_tsv(monkeypatch):
    from open_rosalind.tools import stringdb as stringdb_tools

    class FakeResponse:
        def __init__(self, text):
            self.text = text
            self.status_code = 200

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, text):
            self.text = text
            self.requests = []

        def post(self, url, data=None, timeout=None):
            self.requests.append({"url": url, "data": data, "timeout": timeout})
            return FakeResponse(self.text)

        def close(self):
            return None

    fake_session = FakeSession(
        "stringId_A\tstringId_B\tpreferredName_A\tpreferredName_B\tncbiTaxonId\tscore\tnscore\tfscore\tpscore\tascore\tescore\tdscore\ttscore\n"
        "9606.ENSP00000269305\t9606.ENSP00000354587\tTP53\tMDM2\t9606\t980\t0\t0\t0\t0\t0\t0\t980\n"
    )
    monkeypatch.setattr(stringdb_tools, "make_session", lambda: fake_session)

    out = stringdb_tools.interaction_partners("TP53")
    assert out["count"] == 1
    assert out["records"][0]["preferred_name_b"] == "MDM2"
    assert out["records"][0]["score"] == 980


def test_chembl_search_molecules_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import chembl as chembl_tools

    monkeypatch.setattr(
        chembl_tools,
        "get_json",
        lambda url, params=None, timeout=30: {
            "page_meta": {"total_count": 1},
            "molecules": [
                {
                    "molecule_chembl_id": "CHEMBL25",
                    "pref_name": "imatinib",
                    "molecule_type": "Small molecule",
                    "max_phase": 4,
                    "molecule_properties": {"full_mwt": "493.62", "alogp": "4.2"},
                    "molecule_synonyms": [{"molecule_synonym": "Gleevec"}],
                }
            ],
        },
    )

    out = chembl_tools.search_molecules("imatinib")
    assert out["count"] == 1
    assert out["records"][0]["molecule_chembl_id"] == "CHEMBL25"
    assert out["records"][0]["synonyms"] == ["Gleevec"]


def test_clinicaltrials_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.clinicaltrials_search import handler as ct_handler_module

    monkeypatch.setattr(
        ct_handler_module.clinicaltrials_tools,
        "search_studies",
        lambda condition, status=None, max_results=5, page_size=5, max_pages=1: {
            "query": condition,
            "status": status,
            "count": 1,
            "records": [
                {
                    "nct_id": "NCT01234567",
                    "brief_title": "Trial of TP53 inhibitor",
                    "overall_status": "RECRUITING",
                    "phases": ["PHASE2"],
                    "lead_sponsor": "Open Rosalind Hospital",
                }
            ],
        },
    )

    out = execute_skill_v2("clinicaltrials_search", {"condition": "glioblastoma", "status": "RECRUITING"})
    assert out["annotation"]["kind"] == "clinical_trials"
    assert out["annotation"]["nct_id"] == "NCT01234567"
    assert out["clinicaltrials"]["count"] == 1


def test_string_network_skill_success(monkeypatch):
    from open_rosalind.skills_v2.string_network import handler as string_handler_module

    monkeypatch.setattr(
        string_handler_module.stringdb_tools,
        "interaction_partners",
        lambda identifiers, species=9606, limit=10, required_score=400, network_type="functional", caller_identity="open-rosalind": {
            "mode": "interaction_partners",
            "query_identifiers": [identifiers] if isinstance(identifiers, str) else identifiers,
            "species": species,
            "count": 1,
            "records": [
                {
                    "preferred_name_a": "TP53",
                    "preferred_name_b": "MDM2",
                    "score": 980,
                }
            ],
        },
    )

    out = execute_skill_v2("string_network", {"identifiers": "TP53"})
    assert out["annotation"]["kind"] == "protein_network"
    assert out["annotation"]["top_partner"] == "MDM2"
    assert out["string"]["count"] == 1


def test_chembl_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.chembl_search import handler as chembl_handler_module

    monkeypatch.setattr(
        chembl_handler_module.chembl_tools,
        "search_targets",
        lambda query, max_results=5: {
            "query": query,
            "entity": "target",
            "count": 1,
            "records": [
                {
                    "target_chembl_id": "CHEMBL204",
                    "pref_name": "Epidermal growth factor receptor",
                    "target_type": "SINGLE PROTEIN",
                    "organism": "Homo sapiens",
                }
            ],
        },
    )

    out = execute_skill_v2("chembl_search", {"entity": "target", "query": "EGFR"})
    assert out["annotation"]["kind"] == "chembl"
    assert out["annotation"]["chembl_id"] == "CHEMBL204"
    assert out["chembl"]["count"] == 1


def test_clinvar_variation_fetch_refsnp_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import clinvar_variation as clinvar_variation_tools

    monkeypatch.setattr(
        clinvar_variation_tools,
        "get_json",
        lambda url, params=None, timeout=30: {
            "refsnp_id": "7412",
            "citations": [12345678],
            "dbsnp1_merges": [{"merged_rsid": "3200542"}],
            "primary_snapshot_data": {
                "variant_type": "snv",
                "anchor": "NC_000019.10:0044908821:1:snv",
                "placements_with_allele": [
                    {
                        "alleles": [
                            {"hgvs": "NC_000019.10:g.44908822C>T"},
                            {"hgvs": "NM_000041.4:c.388T>C"},
                        ]
                    }
                ],
                "allele_annotations": [
                    {
                        "frequency": [
                            {
                                "study_name": "1000Genomes",
                                "allele_count": 10,
                                "total_count": 100,
                                "observation": {"seq_id": "NC_000019.10"},
                            }
                        ]
                    }
                ],
            },
        },
    )

    out = clinvar_variation_tools.fetch_refsnp("rs7412")
    assert out["refsnp_id"] == "7412"
    assert out["variant_type"] == "snv"
    assert out["hgvs"][0] == "NC_000019.10:g.44908822C>T"
    assert out["top_frequency"]["allele_frequency"] == 0.1


def test_gnomad_fetch_variant_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import gnomad as gnomad_tools

    monkeypatch.setattr(
        gnomad_tools,
        "post_json",
        lambda url, json_body, timeout=60: {
            "data": {
                "variant": {
                    "variantId": "19-44908822-C-T",
                    "reference_genome": "GRCh38",
                    "exome": {"ac": 102550, "an": 1388698, "af": 0.0738},
                    "genome": {"ac": 11840, "an": 152112, "af": 0.0778},
                    "sortedTranscriptConsequences": [
                        {
                            "gene_symbol": "APOE",
                            "major_consequence": "missense_variant",
                            "transcript_id": "ENST00000252486",
                            "hgvs": "p.Arg176Cys",
                        }
                    ],
                }
            }
        },
    )

    out = gnomad_tools.fetch_variant(variant_id="19-44908822-C-T")
    assert out["found"] is True
    assert out["variant_id"] == "19-44908822-C-T"
    assert out["transcript_consequences"][0]["gene_symbol"] == "APOE"


def test_gwas_catalog_search_associations_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import gwas_catalog as gwas_catalog_tools

    monkeypatch.setattr(
        gwas_catalog_tools,
        "get_json",
        lambda url, params=None, timeout=30: {
            "page": {"totalElements": 1},
            "_embedded": {
                "associations": [
                    {
                        "association_id": 217699926,
                        "accession_id": "GCST90077672",
                        "reported_trait": ["ICD10 J45: Asthma"],
                        "mapped_genes": ["IL6R"],
                        "p_value": 5.0e-17,
                        "locations": ["9:6255967"],
                        "efo_traits": [{"efo_id": "MONDO_0004979", "efo_trait": "asthma"}],
                        "snp_allele": [{"rs_id": "rs4129267", "effect_allele": "C"}],
                        "_links": {"self": {"href": "https://example.org/a/1"}, "snp": {"href": "https://example.org/snp/1"}},
                    }
                ]
            },
        },
    )

    out = gwas_catalog_tools.search_associations(efo_trait="asthma")
    assert out["count"] == 1
    assert out["records"][0]["association_id"] == 217699926
    assert out["records"][0]["mapped_genes"] == ["IL6R"]


def test_opentargets_fetch_target_diseases_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import opentargets as opentargets_tools

    monkeypatch.setattr(
        opentargets_tools,
        "post_json",
        lambda url, json_body, timeout=60: {
            "data": {
                "target": {
                    "id": "ENSG00000160712",
                    "approvedSymbol": "IL6R",
                    "approvedName": "interleukin 6 receptor",
                    "associatedDiseases": {
                        "count": 1,
                        "rows": [
                            {
                                "disease": {"id": "EFO_0000685", "name": "rheumatoid arthritis"},
                                "score": 0.72,
                                "datasourceScores": [{"id": "clinical_precedence", "score": 0.99}],
                            }
                        ],
                    },
                }
            }
        },
    )

    out = opentargets_tools.fetch_target_diseases("ENSG00000160712")
    assert out["approved_symbol"] == "IL6R"
    assert out["records"][0]["disease_name"] == "rheumatoid arthritis"


def test_civic_fetch_variant_evidence_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import civic as civic_tools

    monkeypatch.setattr(
        civic_tools,
        "post_json",
        lambda url, json_body, timeout=60: {
            "data": {
                "variants": {
                    "nodes": [
                        {
                            "id": 12,
                            "name": "V600E",
                            "feature": {"id": 1, "name": "BRAF"},
                            "evidenceItems": {
                                "nodes": [
                                    {
                                        "id": 101,
                                        "description": "Sensitive to therapy.",
                                        "evidenceLevel": "A",
                                        "evidenceType": "PREDICTIVE",
                                        "evidenceDirection": "SUPPORTS",
                                        "significance": "SENSITIVITY_RESPONSE",
                                        "disease": {"name": "melanoma"},
                                        "therapies": [{"name": "vemurafenib"}],
                                    }
                                ]
                            },
                        }
                    ]
                }
            }
        },
    )

    out = civic_tools.fetch_variant_evidence("V600E")
    assert out["count"] == 1
    assert out["records"][0]["feature_name"] == "BRAF"
    assert out["records"][0]["evidence_items"][0]["therapies"] == ["vemurafenib"]


def test_clinvar_variation_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.clinvar_variation_lookup import handler as cv_handler_module

    monkeypatch.setattr(
        cv_handler_module.clinvar_variation_tools,
        "search_clinical_tables",
        lambda terms, max_results=5: {
            "query": terms,
            "count": 1,
            "records": [{"identifier": "rs7412"}],
        },
    )
    monkeypatch.setattr(
        cv_handler_module.clinvar_variation_tools,
        "fetch_refsnp",
        lambda refsnp_id: {
            "refsnp_id": "7412",
            "variant_type": "snv",
            "anchor": "NC_000019.10:0044908821:1:snv",
            "top_frequency": {"study_name": "1000Genomes", "allele_frequency": 0.1},
        },
    )

    out = execute_skill_v2("clinvar_variation_lookup", {"query": "rs7412"})
    assert out["annotation"]["kind"] == "clinvar_variation"
    assert out["annotation"]["refsnp_id"] == "7412"
    assert any("Resolved query" in note for note in out["notes"])


def test_gnomad_variant_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gnomad_variant_lookup import handler as gnomad_handler_module

    monkeypatch.setattr(
        gnomad_handler_module.gnomad_tools,
        "fetch_variant",
        lambda variant_id=None, rsid=None, dataset="gnomad_r4": {
            "query": variant_id or rsid,
            "dataset": dataset,
            "found": True,
            "variant_id": "19-44908822-C-T",
            "exome": {"af": 0.0738},
            "genome": {"af": 0.0778},
            "transcript_consequences": [{"gene_symbol": "APOE", "major_consequence": "missense_variant"}],
        },
    )

    out = execute_skill_v2("gnomad_variant_lookup", {"variant_id": "19-44908822-C-T"})
    assert out["annotation"]["kind"] == "gnomad_variant"
    assert out["annotation"]["gene_symbol"] == "APOE"
    assert out["annotation"]["exome_af"] == 0.0738


def test_gwas_catalog_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.gwas_catalog_search import handler as gwas_handler_module

    monkeypatch.setattr(
        gwas_handler_module.gwas_catalog_tools,
        "search_associations",
        lambda efo_trait=None, mapped_gene=None, size=5: {
            "query": efo_trait or mapped_gene,
            "count": 1,
            "records": [
                {
                    "association_id": 217699926,
                    "accession_id": "GCST90077672",
                    "reported_trait": ["ICD10 J45: Asthma"],
                    "mapped_genes": ["IL6R"],
                    "p_value": 5.0e-17,
                }
            ],
        },
    )

    out = execute_skill_v2("gwas_catalog_search", {"mapped_gene": "IL6R", "mode": "associations"})
    assert out["annotation"]["kind"] == "gwas_catalog"
    assert out["annotation"]["accession_id"] == "GCST90077672"
    assert out["annotation"]["mapped_genes"] == ["IL6R"]


def test_opentargets_target_disease_skill_success(monkeypatch):
    from open_rosalind.skills_v2.opentargets_target_disease import handler as ot_handler_module

    monkeypatch.setattr(
        ot_handler_module.opentargets_tools,
        "search",
        lambda query: {
            "query": query,
            "count": 1,
            "hits": [{"id": "ENSG00000160712", "entity": "target", "approved_symbol": "IL6R"}],
        },
    )
    monkeypatch.setattr(
        ot_handler_module.opentargets_tools,
        "fetch_target_diseases",
        lambda ensembl_id: {
            "ensembl_id": ensembl_id,
            "approved_symbol": "IL6R",
            "approved_name": "interleukin 6 receptor",
            "count": 1,
            "records": [{"disease_id": "EFO_0000685", "disease_name": "rheumatoid arthritis", "score": 0.72}],
        },
    )

    out = execute_skill_v2("opentargets_target_disease", {"query": "IL6R"})
    assert out["annotation"]["kind"] == "opentargets_target_disease"
    assert out["annotation"]["approved_symbol"] == "IL6R"
    assert out["annotation"]["top_disease_name"] == "rheumatoid arthritis"


def test_civic_variant_evidence_skill_success(monkeypatch):
    from open_rosalind.skills_v2.civic_variant_evidence import handler as civic_handler_module

    monkeypatch.setattr(
        civic_handler_module.civic_tools,
        "typeahead",
        lambda query: {"query": query, "count": 1, "records": [{"id": 12, "name": "V600E", "result_type": "VARIANT"}]},
    )
    monkeypatch.setattr(
        civic_handler_module.civic_tools,
        "fetch_variant_evidence",
        lambda variant_name, first=3: {
            "query": variant_name,
            "count": 1,
            "records": [
                {
                    "name": "V600E",
                    "feature_name": "BRAF",
                    "evidence_items": [
                        {
                            "evidence_level": "A",
                            "evidence_type": "PREDICTIVE",
                            "significance": "SENSITIVITY_RESPONSE",
                            "disease_name": "melanoma",
                        }
                    ],
                }
            ],
        },
    )

    out = execute_skill_v2("civic_variant_evidence", {"query": "V600E"})
    assert out["annotation"]["kind"] == "civic_variant_evidence"
    assert out["annotation"]["feature_name"] == "BRAF"
    assert out["annotation"]["top_disease_name"] == "melanoma"


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
        assert max_results == 5
        if query == "TP53":
            return {
                "count": 1,
                "hits": [
                    {
                        "accession": "Q12888",
                        "name": "TP53-binding protein 1",
                        "organism": "Homo sapiens",
                    }
                ],
            }
        if query == "gene_exact:TP53":
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
        raise AssertionError(f"unexpected query: {query}")

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
    assert any("Resolved gene symbol" in note for note in out["notes"])
    assert any("gene-specific search fallback" in note for note in out["notes"])


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


def test_bgee_lookup_expression_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import bgee as bgee_tools

    class FakeResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, data):
            self.data = data
            self.requests = []

        def get(self, url, params=None, headers=None, timeout=None):
            self.requests.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
            return FakeResponse(self.data)

        def close(self):
            return None

    fake_session = FakeSession(
        {
            "results": {
                "bindings": [
                    {
                        "anat": {"value": "http://purl.obolibrary.org/obo/UBERON_0000992"},
                        "anatName": {"value": "ovary"},
                        "score": {"value": "97.75519"},
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(bgee_tools, "make_session", lambda: fake_session)

    out = bgee_tools.lookup_expression("ENSG00000141510")
    assert out["count"] == 1
    assert out["records"][0]["anatomical_entity_id"] == "UBERON_0000992"
    assert out["records"][0]["expression_score"] == 97.75519


def test_human_protein_atlas_fetch_gene_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import human_protein_atlas as hpa_tools

    class FakeResponse:
        def __init__(self, data, status_code=200):
            self._data = data
            self.status_code = status_code

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, data):
            self.data = data
            self.requests = []

        def get(self, url, headers=None, timeout=None):
            self.requests.append({"url": url, "headers": headers, "timeout": timeout})
            return FakeResponse(self.data)

        def close(self):
            return None

    fake_session = FakeSession(
        {
            "Gene": "TP53",
            "Ensembl": "ENSG00000141510",
            "Gene description": "Tumor protein p53",
            "Uniprot": ["P04637"],
            "Protein class": ["Cancer-related genes"],
            "Subcellular main location": ["Nucleoplasm"],
            "RNA tissue specificity": "Low tissue specificity",
        }
    )
    monkeypatch.setattr(hpa_tools, "make_session", lambda: fake_session)

    out = hpa_tools.fetch_gene("ENSG00000141510")
    assert out["found"] is True
    assert out["records"][0]["gene"] == "TP53"
    assert out["records"][0]["uniprot_ids"] == ["P04637"]
    assert out["records"][0]["subcellular_main_location"] == ["Nucleoplasm"]


def test_rcsb_pdb_search_entries_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import rcsb_pdb as rcsb_pdb_tools

    monkeypatch.setattr(
        rcsb_pdb_tools,
        "post_json",
        lambda url, json_body, timeout=60: {
            "total_count": 2,
            "result_set": [
                {"identifier": "4HHB", "score": 1.0},
                {"identifier": "1A3N", "score": 0.82},
            ],
        },
    )

    out = rcsb_pdb_tools.search_entries("hemoglobin")
    assert out["count"] == 2
    assert out["records"][0]["entry_id"] == "4HHB"


def test_rcsb_pdb_fetch_entry_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import rcsb_pdb as rcsb_pdb_tools

    monkeypatch.setattr(
        rcsb_pdb_tools,
        "get_json",
        lambda url, params=None, timeout=60: {
            "struct": {"title": "Hemoglobin beta chain complex"},
            "rcsb_entry_info": {
                "experimental_method": "X-RAY DIFFRACTION",
                "resolution_combined": [1.74],
                "polymer_entity_count": 2,
                "nonpolymer_entity_count": 1,
                "assembly_count": 1,
                "molecular_weight": 64.5,
                "structure_determination_methodology": "experimental",
            },
            "rcsb_primary_citation": {
                "title": "Human hemoglobin structure",
                "year": 1984,
                "pdbx_database_id_DOI": "10.1016/example",
            },
            "rcsb_accession_info": {
                "deposit_date": "1984-03-07T00:00:00.000+00:00",
                "initial_release_date": "1984-07-17T00:00:00.000+00:00",
                "revision_date": "2024-05-22T00:00:00.000+00:00",
            },
            "rcsb_entry_container_identifiers": {
                "entry_id": "4HHB",
                "polymer_entity_ids": ["1", "2"],
                "non_polymer_entity_ids": ["3"],
                "pubmed_id": 6726807,
            },
            "exptl": [{"method": "X-RAY DIFFRACTION"}],
            "refine": [{"ls_d_res_high": 1.74}],
        },
    )

    out = rcsb_pdb_tools.fetch_entry("4hhb")
    assert out["found"] is True
    assert out["entry_id"] == "4HHB"
    assert out["resolution"] == 1.74
    assert out["experimental_methods"] == ["X-RAY DIFFRACTION"]


def test_pharmgkb_search_clinical_annotations_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import pharmgkb as pharmgkb_tools

    monkeypatch.setattr(
        pharmgkb_tools,
        "get_json",
        lambda url, params=None, timeout=60: {
            "status": "success",
            "data": [
                {
                    "id": 981239556,
                    "accessionId": "PA166134613",
                    "name": "rs104894541 (VKORC1); warfarin",
                    "score": 0.25,
                    "types": ["Dosage"],
                    "levelOfEvidence": {"term": "Level 3"},
                    "relatedChemicals": [{"name": "warfarin"}],
                    "location": {
                        "genes": [{"symbol": "VKORC1"}],
                        "variant": {"symbol": "rs104894541"},
                        "rsid": "rs104894541",
                    },
                }
            ],
        },
    )

    out = pharmgkb_tools.search_clinical_annotations(chemical_name="warfarin")
    assert out["count"] == 1
    assert out["records"][0]["accession_id"] == "PA166134613"
    assert out["records"][0]["gene_symbols"] == ["VKORC1"]


def test_pharmgkb_fetch_clinical_annotation_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import pharmgkb as pharmgkb_tools

    class FakeResponse:
        def __init__(self, data, status_code=200):
            self._data = data
            self.status_code = status_code

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, data):
            self.data = data
            self.requests = []

        def get(self, url, headers=None, timeout=None):
            self.requests.append({"url": url, "headers": headers, "timeout": timeout})
            return FakeResponse(self.data)

        def close(self):
            return None

    fake_session = FakeSession(
        {
            "status": "success",
            "data": {
                "id": 981239556,
                "accessionId": "PA166134613",
                "name": "rs104894541 (VKORC1); warfarin",
                "score": 0.25,
                "types": ["Dosage"],
                "levelOfEvidence": {"term": "Level 3"},
                "relatedChemicals": [{"name": "warfarin"}],
                "relatedVariations": [{"symbol": "CA115414", "name": "VKORC1 variant", "objCls": "Allele"}],
                "allelePhenotypes": [{"allele": "CC", "phenotype": "Resistant", "limitedEvidence": False}],
                "location": {
                    "displayName": "rs104894541",
                    "rsid": "rs104894541",
                    "genes": [{"symbol": "VKORC1"}],
                    "variant": {"symbol": "rs104894541"},
                },
            },
        }
    )
    monkeypatch.setattr(pharmgkb_tools, "make_session", lambda: fake_session)

    out = pharmgkb_tools.fetch_clinical_annotation(accession_id="PA166134613")
    assert out["found"] is True
    assert out["accession_id"] == "PA166134613"
    assert out["gene_symbols"] == ["VKORC1"]
    assert out["allele_phenotypes"][0]["allele"] == "CC"


def test_ncbi_blast_run_search_tool_summarizes_hits():
    from open_rosalind.tools import ncbi_blast as ncbi_blast_tools

    class FakeResponse:
        def __init__(self, text, headers=None, json_data=None):
            self.text = text
            self.headers = headers or {"content-type": "application/json"}
            self._json_data = json_data
            self.content = text.encode("utf-8")
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            if self._json_data is not None:
                return self._json_data
            return {}

    class FakeSession:
        def __init__(self, responses):
            self.responses = responses
            self.headers = {}

        def request(self, method, url, **kwargs):
            return self.responses.pop(0)

        def close(self):
            return None

    payload = {
        "BlastOutput2": [
            {
                "report": {
                    "results": {
                        "search": {
                            "query_title": "q1",
                            "hits": [
                                {
                                    "description": [{"accession": "P04637", "title": "Cellular tumor antigen p53"}],
                                    "hsps": [{"evalue": 1e-50, "bit_score": 250.0}],
                                }
                            ],
                        }
                    }
                }
            }
        ]
    }
    fake_session = FakeSession(
        [
            FakeResponse("RID = TEST123\nRTOE = 3\n", headers={"content-type": "text/plain"}),
            FakeResponse("Status=READY\nThereAreHits=yes\n", headers={"content-type": "text/plain"}),
            FakeResponse(json.dumps(payload), json_data=payload),
        ]
    )

    current = [0.0]

    def clock() -> float:
        return current[0]

    def sleep(seconds: float) -> None:
        current[0] += seconds

    out = ncbi_blast_tools.run_search(
        "blastp",
        "swissprot",
        ">q1\nMEEPQSDPSV",
        email="test@example.com",
        session=fake_session,
        sleep_fn=sleep,
        clock_fn=clock,
    )
    assert out["status"] == "READY"
    assert out["has_hits"] is True
    assert out["query_summaries"][0]["top_hits"][0]["accession"] == "P04637"


def test_bgee_expression_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.bgee_expression_lookup import handler as bgee_handler_module

    monkeypatch.setattr(
        bgee_handler_module.ensembl_tools,
        "lookup_gene",
        lambda symbol, species="homo_sapiens": {
            "found": True,
            "ensembl_gene_id": "ENSG00000141510",
            "symbol": "TP53",
        },
    )
    monkeypatch.setattr(
        bgee_handler_module.bgee_tools,
        "lookup_expression",
        lambda ensembl_id, max_results=5: {
            "ensembl_id": ensembl_id,
            "count": 1,
            "records": [{"anatomical_entity_name": "ovary", "expression_score": 97.7}],
        },
    )

    out = execute_skill_v2("bgee_expression_lookup", {"gene_symbol": "TP53"})
    assert out["annotation"]["kind"] == "bgee_expression"
    assert out["annotation"]["ensembl_id"] == "ENSG00000141510"
    assert out["annotation"]["top_anatomical_entity"] == "ovary"


def test_human_protein_atlas_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.human_protein_atlas_lookup import handler as hpa_handler_module

    monkeypatch.setattr(
        hpa_handler_module.ensembl_tools,
        "lookup_gene",
        lambda symbol, species="homo_sapiens": {
            "found": True,
            "ensembl_gene_id": "ENSG00000141510",
            "symbol": "TP53",
        },
    )
    monkeypatch.setattr(
        hpa_handler_module.hpa_tools,
        "fetch_gene",
        lambda ensembl_id: {
            "found": True,
            "count": 1,
            "records": [
                {
                    "gene": "TP53",
                    "ensembl_id": ensembl_id,
                    "uniprot_ids": ["P04637"],
                    "subcellular_main_location": ["Nucleoplasm"],
                    "rna_tissue_specificity": "Low tissue specificity",
                }
            ],
        },
    )

    out = execute_skill_v2("human_protein_atlas_lookup", {"gene_symbol": "TP53"})
    assert out["annotation"]["kind"] == "human_protein_atlas"
    assert out["annotation"]["uniprot_id"] == "P04637"
    assert out["annotation"]["top_subcellular_location"] == "Nucleoplasm"


def test_rcsb_pdb_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.rcsb_pdb_lookup import handler as rcsb_handler_module

    monkeypatch.setattr(
        rcsb_handler_module.rcsb_pdb_tools,
        "search_entries",
        lambda query, max_results=5: {
            "query": query,
            "count": 1,
            "records": [{"entry_id": "4HHB", "score": 1.0}],
        },
    )
    monkeypatch.setattr(
        rcsb_handler_module.rcsb_pdb_tools,
        "fetch_entry",
        lambda entry_id: {
            "found": True,
            "entry_id": entry_id,
            "title": "Human hemoglobin",
            "experimental_methods": ["X-RAY DIFFRACTION"],
            "resolution": 1.74,
            "polymer_entity_count": 2,
        },
    )

    out = execute_skill_v2("rcsb_pdb_lookup", {"query": "hemoglobin"})
    assert out["annotation"]["kind"] == "rcsb_pdb"
    assert out["annotation"]["entry_id"] == "4HHB"
    assert out["annotation"]["resolution"] == 1.74


def test_pharmgkb_clinical_annotation_skill_success(monkeypatch):
    from open_rosalind.skills_v2.pharmgkb_clinical_annotation import handler as pharmgkb_handler_module

    monkeypatch.setattr(
        pharmgkb_handler_module.pharmgkb_tools,
        "search_clinical_annotations",
        lambda chemical_name=None, gene_symbol=None, variant_symbol=None, max_results=5: {
            "count": 1,
            "records": [{"id": 981239556, "accession_id": "PA166134613"}],
        },
    )
    monkeypatch.setattr(
        pharmgkb_handler_module.pharmgkb_tools,
        "fetch_clinical_annotation",
        lambda annotation_id=None, accession_id=None: {
            "found": True,
            "id": 981239556,
            "accession_id": accession_id or "PA166134613",
            "name": "rs104894541 (VKORC1); warfarin",
            "level_of_evidence": "Level 3",
            "gene_symbols": ["VKORC1"],
            "chemical_names": ["warfarin"],
            "variant_symbol": "rs104894541",
            "allele_phenotypes": [{"allele": "CC"}],
        },
    )

    out = execute_skill_v2("pharmgkb_clinical_annotation", {"chemical_name": "warfarin"})
    assert out["annotation"]["kind"] == "pharmgkb_clinical_annotation"
    assert out["annotation"]["accession_id"] == "PA166134613"
    assert out["annotation"]["gene_symbol"] == "VKORC1"


def test_ncbi_blast_search_skill_success(monkeypatch):
    from open_rosalind.skills_v2.ncbi_blast_search import handler as blast_handler_module

    monkeypatch.setattr(
        blast_handler_module.ncbi_blast_tools,
        "run_search",
        lambda program, database, query_fasta, email=None, max_hits=5, max_queries=5, wait_timeout_sec=900: {
            "program": program,
            "database": database,
            "rid": "TEST123",
            "status": "READY",
            "has_hits": True,
            "query_summaries": [
                {
                    "hit_count_returned": 1,
                    "top_hits": [{"accession": "P04637", "title": "Cellular tumor antigen p53", "evalue": 1e-50}],
                }
            ],
        },
    )

    out = execute_skill_v2(
        "ncbi_blast_search",
        {
            "program": "blastp",
            "database": "swissprot",
            "query_fasta": ">q1\nMEEPQSDPSV",
            "email": "test@example.com",
        },
    )
    assert out["annotation"]["kind"] == "ncbi_blast"
    assert out["annotation"]["rid"] == "TEST123"
    assert out["annotation"]["top_accession"] == "P04637"


def test_efo_search_terms_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import efo as efo_tools

    monkeypatch.setattr(
        efo_tools,
        "get_json",
        lambda url, params=None, timeout=30: {
            "response": {
                "docs": [
                    {
                        "iri": "http://purl.obolibrary.org/obo/HP_0002099",
                        "label": "Asthma",
                        "obo_id": "HP:0002099",
                        "short_form": "HP_0002099",
                        "ontology_prefix": "EFO",
                        "description": ["Asthma description"],
                        "exact_synonyms": ["Bronchial asthma"],
                        "related_synonyms": ["Reactive airway disease"],
                        "is_obsolete": False,
                        "has_children": True,
                    }
                ]
            }
        },
    )

    out = efo_tools.search_terms("asthma")
    assert out["count"] == 1
    assert out["records"][0]["label"] == "Asthma"
    assert out["records"][0]["synonyms"] == ["Bronchial asthma", "Reactive airway disease"]


def test_pubchem_lookup_compound_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import pubchem as pubchem_tools

    def fake_get_json(url, params=None, timeout=30):
        if "/cids/JSON" in url:
            return {"IdentifierList": {"CID": [2244]}}
        if "/property/" in url:
            return {
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 2244,
                            "MolecularFormula": "C9H8O4",
                            "MolecularWeight": "180.16",
                            "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                            "IUPACName": "2-acetyloxybenzoic acid",
                        }
                    ]
                }
            }
        return {
            "InformationList": {
                "Information": [
                    {"CID": 2244, "Title": "Aspirin"},
                    {"CID": 2244, "Description": "Analgesic", "DescriptionSourceName": "Test"},
                ]
            }
        }

    monkeypatch.setattr(pubchem_tools, "get_json", fake_get_json)

    out = pubchem_tools.lookup_compound(query="aspirin")
    assert out["found"] is True
    assert out["records"][0]["cid"] == 2244
    assert out["records"][0]["molecular_formula"] == "C9H8O4"


def test_chebi_fetch_compound_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import chebi as chebi_tools

    monkeypatch.setattr(
        chebi_tools,
        "get_json",
        lambda url, params=None, timeout=30: {
            "chebi_accession": "CHEBI:27732",
            "name": "caffeine",
            "definition": "A trimethylxanthine.",
            "ascii_name": "caffeine",
            "stars": 3,
            "formula": "C8H10N4O2",
            "smiles": "Cn1cnc2n(C)c(=O)n(C)c(=O)c12",
            "mass": 194.19,
            "names": {"SYNONYM": [{"name": "1,3,7-trimethylxanthine"}]},
            "ontology_relations": {"incoming_relations": [{}], "outgoing_relations": [{}, {}]},
        },
    )

    out = chebi_tools.fetch_compound("CHEBI:27732")
    assert out["found"] is True
    assert out["records"][0]["name"] == "caffeine"
    assert out["records"][0]["incoming_relation_count"] == 1


def test_bindingdb_lookup_ligands_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import bindingdb as bindingdb_tools

    class FakeResponse:
        def __init__(self, data):
            self._data = data
            self.status_code = 200

        def json(self):
            return self._data

        def raise_for_status(self):
            return None

    class FakeSession:
        def __init__(self, data):
            self.data = data
            self.requests = []

        def get(self, url, params=None, timeout=None):
            self.requests.append({"url": url, "params": params, "timeout": timeout})
            return FakeResponse(self.data)

        def close(self):
            return None

    fake_session = FakeSession(
        {
            "getLindsByUniprotsResponse": {
                "affinities": [
                    {
                        "query": "Cellular tumor antigen p53",
                        "monomerid": "50463351",
                        "smile": "O=C1CCCN1",
                        "affinity_type": "EC50",
                        "affinity": "12",
                        "pmid": "30075999",
                        "doi": "10.1016/example",
                    }
                ]
            }
        }
    )
    monkeypatch.setattr(bindingdb_tools, "make_session", lambda: fake_session)

    out = bindingdb_tools.lookup_ligands(uniprot_id="P04637")
    assert out["count"] == 1
    assert out["records"][0]["affinity_type"] == "EC50"
    assert out["records"][0]["pmid"] == "30075999"


def test_cellxgene_fetch_collection_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import cellxgene as cellxgene_tools

    monkeypatch.setattr(
        cellxgene_tools,
        "get_json",
        lambda url, params=None, timeout=60: {
            "collection_id": "db468083-041c-41ca-8f6f-bf991a070adf",
            "name": "Endothelial atlas",
            "description": "Collection description",
            "collection_url": "https://cellxgene.cziscience.com/collections/db468083-041c-41ca-8f6f-bf991a070adf",
            "doi": "10.1016/example",
            "contact_name": "Sheng Zhong",
            "contact_email": "szhong@example.org",
            "curator_name": "Curator",
            "datasets": [
                {
                    "dataset_id": "ds1",
                    "title": "Dataset 1",
                    "cell_count": 59605,
                    "organism": [{"label": "Homo sapiens"}],
                    "tissue": [{"label": "endothelial cell"}],
                    "cell_type": [{"label": "endothelial cell of umbilical vein"}],
                    "disease": [{"label": "normal"}],
                    "assay": [{"label": "10x 3' v2"}],
                    "feature_count": 20000,
                    "is_primary_data": True,
                    "explorer_url": "https://cellxgene.cziscience.com/e/ds1.cxg/",
                }
            ],
        },
    )

    out = cellxgene_tools.fetch_collection("db468083-041c-41ca-8f6f-bf991a070adf")
    assert out["found"] is True
    assert out["records"][0]["collection_name"] == "Endothelial atlas"
    assert out["records"][0]["datasets"][0]["dataset_id"] == "ds1"


def test_pride_fetch_project_tool_normalizes_records(monkeypatch):
    from open_rosalind.tools import pride as pride_tools

    monkeypatch.setattr(
        pride_tools,
        "get_json",
        lambda url, params=None, timeout=60: {
            "accession": "PXD001357",
            "title": "Milk consumption from ancient calculus",
            "doi": "10.1016/example",
            "publicationDate": "2014-01-01",
            "submissionDate": "2013-01-01",
            "projectDescription": "Project description",
            "organisms": ["Homo sapiens"],
            "organismParts": ["dental calculus"],
            "experimentTypes": ["shotgun proteomics"],
            "keywords": ["ancient proteomics"],
            "totalFileDownloads": 100,
        },
    )

    out = pride_tools.fetch_project("PXD001357")
    assert out["found"] is True
    assert out["records"][0]["accession"] == "PXD001357"
    assert out["records"][0]["organisms"] == ["Homo sapiens"]


def test_efo_term_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.efo_term_lookup import handler as efo_handler_module

    monkeypatch.setattr(
        efo_handler_module.efo_tools,
        "search_terms",
        lambda query, max_results=5: {
            "query": query,
            "count": 1,
            "records": [{"iri": "http://purl.obolibrary.org/obo/HP_0002099", "obo_id": "HP:0002099"}],
        },
    )
    monkeypatch.setattr(
        efo_handler_module.efo_tools,
        "fetch_term",
        lambda term_id: {
            "found": True,
            "count": 1,
            "records": [{"iri": term_id, "label": "Asthma", "obo_id": "HP:0002099", "has_children": True}],
        },
    )

    out = execute_skill_v2("efo_term_lookup", {"query": "asthma"})
    assert out["annotation"]["kind"] == "efo_term"
    assert out["annotation"]["label"] == "Asthma"


def test_pubchem_compound_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.pubchem_compound_lookup import handler as pubchem_handler_module

    monkeypatch.setattr(
        pubchem_handler_module.pubchem_tools,
        "lookup_compound",
        lambda query=None, cid=None: {
            "found": True,
            "count": 1,
            "records": [
                {
                    "cid": 2244,
                    "molecular_formula": "C9H8O4",
                    "molecular_weight": "180.16",
                    "iupac_name": "2-acetyloxybenzoic acid",
                    "descriptions": [{"title": "Aspirin"}],
                }
            ],
        },
    )

    out = execute_skill_v2("pubchem_compound_lookup", {"query": "aspirin"})
    assert out["annotation"]["kind"] == "pubchem_compound"
    assert out["annotation"]["cid"] == 2244


def test_chebi_compound_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.chebi_compound_lookup import handler as chebi_handler_module

    monkeypatch.setattr(
        chebi_handler_module.chebi_tools,
        "search_compounds",
        lambda query, max_results=5: {
            "query": query,
            "count": 1,
            "records": [{"chebi_accession": "CHEBI:27732"}],
        },
    )
    monkeypatch.setattr(
        chebi_handler_module.chebi_tools,
        "fetch_compound",
        lambda chebi_id: {
            "found": True,
            "count": 1,
            "records": [{"chebi_accession": chebi_id, "name": "caffeine", "definition": "A trimethylxanthine."}],
        },
    )

    out = execute_skill_v2("chebi_compound_lookup", {"query": "caffeine"})
    assert out["annotation"]["kind"] == "chebi_compound"
    assert out["annotation"]["chebi_accession"] == "CHEBI:27732"


def test_bindingdb_target_ligands_skill_success(monkeypatch):
    from open_rosalind.skills_v2.bindingdb_target_ligands import handler as bindingdb_handler_module

    monkeypatch.setattr(
        bindingdb_handler_module.bindingdb_tools,
        "lookup_ligands",
        lambda uniprot_id=None, pdb_id=None, max_results=5: {
            "query_type": "uniprot",
            "query": uniprot_id or pdb_id,
            "count": 1,
            "records": [{"affinity_type": "EC50", "affinity": "12", "pmid": "30075999"}],
        },
    )

    out = execute_skill_v2("bindingdb_target_ligands", {"uniprot_id": "P04637"})
    assert out["annotation"]["kind"] == "bindingdb"
    assert out["annotation"]["top_affinity_type"] == "EC50"


def test_cellxgene_collection_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.cellxgene_collection_lookup import handler as cellxgene_handler_module

    monkeypatch.setattr(
        cellxgene_handler_module.cellxgene_tools,
        "fetch_collection",
        lambda collection_id, max_results=5: {
            "found": True,
            "count": 1,
            "records": [{"collection_id": collection_id, "collection_name": "Endothelial atlas", "n_datasets": 1}],
        },
    )

    out = execute_skill_v2("cellxgene_collection_lookup", {"collection_id": "db468083-041c-41ca-8f6f-bf991a070adf"})
    assert out["annotation"]["kind"] == "cellxgene_collection"
    assert out["annotation"]["collection_name"] == "Endothelial atlas"


def test_pride_project_lookup_skill_success(monkeypatch):
    from open_rosalind.skills_v2.pride_project_lookup import handler as pride_handler_module

    monkeypatch.setattr(
        pride_handler_module.pride_tools,
        "search_projects",
        lambda keyword, max_results=5: {
            "query": keyword,
            "count": 1,
            "records": [{"accession": "PXD001357"}],
        },
    )
    monkeypatch.setattr(
        pride_handler_module.pride_tools,
        "fetch_project",
        lambda accession: {
            "found": True,
            "count": 1,
            "records": [{"accession": accession, "title": "Milk consumption from ancient calculus", "doi": "10.1016/example"}],
        },
    )

    out = execute_skill_v2("pride_project_lookup", {"query": "proteomics"})
    assert out["annotation"]["kind"] == "pride_project"
    assert out["annotation"]["accession"] == "PXD001357"
