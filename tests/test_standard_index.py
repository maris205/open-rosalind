from __future__ import annotations

import gzip

from open_rosalind.localdb.build_standard_index import StandardIndexBuilder, StandardIndexConfig


def test_standard_index_builder_creates_fts_and_blast_fasta(tmp_path):
    root = tmp_path / "standard"
    raw = root / "raw"
    (raw / "hgnc").mkdir(parents=True)
    (raw / "reactome").mkdir(parents=True)
    (raw / "go").mkdir(parents=True)
    (raw / "clinvar").mkdir(parents=True)
    (raw / "uniprot").mkdir(parents=True)

    (raw / "hgnc" / "hgnc_complete_set.txt").write_text(
        "hgnc_id\tsymbol\tname\talias_symbol\talias_name\tprev_symbol\tprev_name\tgene_group\tuniprot_ids\tomim_id\tentrez_id\tensembl_gene_id\tlocation\n"
        "HGNC:1100\tBRCA1\tBRCA1 DNA repair associated\tRNF53\tbreast cancer 1\t\t\tDNA repair\tP38398\t113705\t672\tENSG00000012048\t17q21.31\n",
        encoding="utf-8",
    )
    (raw / "reactome" / "ReactomePathways.txt").write_text(
        "R-HSA-73894\tDNA Repair\tHomo sapiens\n",
        encoding="utf-8",
    )
    (raw / "go" / "go-basic.obo").write_text(
        "[Term]\nid: GO:0006281\nname: DNA repair\nnamespace: biological_process\ndef: \"The process of restoring DNA.\" []\n",
        encoding="utf-8",
    )
    (raw / "clinvar" / "gene_specific_summary.txt").write_text(
        "#Symbol\tGeneID\tTotal_submissions\tTotal_alleles\tSubmissions_reporting_this_gene\tAlleles_reported_Pathogenic_Likely_pathogenic\tGene_MIM_number\tNumber_uncertain\tNumber_with_conflicts\n"
        "BRCA1\t672\t10\t9\t8\t7\t113705\t1\t0\n",
        encoding="utf-8",
    )
    with gzip.open(raw / "uniprot" / "uniprot_sprot.fasta.gz", "wt", encoding="utf-8") as handle:
        handle.write(">sp|P38398|BRCA1_HUMAN Breast cancer type 1 susceptibility protein OS=Homo sapiens GN=BRCA1\nMDSALRVEEVQNVINAMQKILECPICLE\n")

    config = StandardIndexConfig(
        root=root,
        index_dir=root / "index",
        db_path=root / "index" / "standard.sqlite",
        blast_dir=root / "index" / "blast",
        limits={
            "hgnc": 0,
            "ncbi_gene_human": 0,
            "reactome_human": 0,
            "go_terms": 0,
            "clinvar_gene": 0,
            "clinvar_variants": 0,
            "uniprot_fasta": 0,
            "pubmed": 0,
        },
        make_blast=False,
    )
    builder = StandardIndexBuilder(config)
    result = builder.build()

    assert result["counts"]["hgnc"] == 1
    assert result["counts"]["reactome_human"] == 1
    assert result["counts"]["go_terms"] == 1
    assert result["counts"]["clinvar_gene"] == 1
    assert (root / "index" / "standard.sqlite").exists()
    assert (root / "index" / "blast" / "swissprot.fasta").read_text(encoding="utf-8").startswith(">sp|P38398")

    hits = builder.search("BRCA1 DNA repair")
    assert hits
    assert hits[0]["kind"] in {"hgnc_gene", "reactome_pathway", "go_term", "clinvar_gene_summary"}
