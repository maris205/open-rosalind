# Developer Skill Samples and Actual Results

Direct `skills_v2` calls from the current Open-Rosalind build on `mvp4`.

- Sample date: 2026-05-07 UTC
- Endpoint: `POST /api/skillsv2/{name}/run`

## 1. `protein_structure_summary` with `{"accession":"P04637"}`

- Result:
  - Returned TP53 AlphaFold DB structure metadata
  - Primary model ID: `AF-P04637-F1`
  - Mean pLDDT: `75.06`

## 2. `clinvar_search` with `{"gene_symbol":"TP53","mutation":"R175H"}`

- Result:
  - Built query `TP53[gene] AND R175H`
  - Returned ClinVar accession `VCV000012374`
  - Germline significance: `Pathogenic`
  - Oncogenicity: `Oncogenic`

## 3. `literature_topic_summary` with `{"query":"CRISPR base editing","max_results":5}`

- Result:
  - Annotation reported `5` hits
  - Top PMIDs: `38308006`, `33449100`, `30835493`, `31727474`, `32833534`

## 4. `reactome_pathway_lookup` with `{"query":"TP53","species":"Homo sapiens"}`

- Result:
  - Resolved to Reactome pathway `R-HSA-6804754`
  - Pathway name: `Regulation of TP53 Expression`
  - Event count: `5`

## 5. `go_term_lookup` with `{"query":"apoptotic process"}`

- Result:
  - Resolved to GO term `GO:0006915`
  - Name: `apoptotic process`
  - Aspect: `biological_process`

## 6. `ensembl_gene_lookup` with `{"symbol":"TP53","species":"homo_sapiens"}`

- Result:
  - Returned Ensembl gene `ENSG00000141510`
  - Biotype: `protein_coding`
  - Canonical transcript: `ENST00000269305.9`

## 7. `ncbi_gene_lookup` with `{"query":"TP53","species":"Homo sapiens"}`

- Result:
  - Resolved to NCBI Gene ID `7157`
  - Chromosome: `17`
  - Map location: `17p13.1`

## 8. `gene_cross_reference` with `{"query":"TP53","species":"homo_sapiens"}`

- Result:
  - Combined Ensembl gene `ENSG00000141510` with NCBI Gene `7157`
  - HGNC ID `HGNC:11998` included
  - OMIM ID `191170` included

## 9. `string_network` with `{"identifiers":"TP53","mode":"interaction_partners"}`

- Result:
  - Returned `10` interaction-partner records
  - Top partner: `SFN`
  - Top score: `0.999`

## 10. `clinicaltrials_search` with `{"condition":"glioblastoma","status":"RECRUITING"}`

- Result:
  - Returned `5` recruiting studies
  - Top study: `NCT05432518`
  - Title: `Pilot Trial for Treatment of Recurrent Glioblastoma`

## 11. `pubchem_compound_lookup` with `{"query":"aspirin"}`

- Result:
  - Returned PubChem CID `2244`
  - Compound name: `Aspirin`
  - Molecular formula: `C9H8O4`

## 12. `ncbi_blast_search` with `{"program":"blastp","database":"swissprot","query_fasta":">q1\\nMVKVGVNGFGRIGRLVTRA"}`

- Result:
  - Returned annotation kind `ncbi_blast` with `n_records: 0`
  - Confidence: `0.0`
  - Note: `NCBI BLAST search failed: email is required for NCBI BLAST or via NCBI_EMAIL`

## Observations

- The newer `skills_v2` modules return structured data and are usable through the developer endpoint.
- `ncbi_blast_search` currently fails without `NCBI_EMAIL`.
- Cross-reference style skills such as `gene_cross_reference` are working and produce compact ID mappings.
