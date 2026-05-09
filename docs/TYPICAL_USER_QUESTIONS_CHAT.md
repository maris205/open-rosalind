# Typical User Questions and Actual Results

Chat endpoint samples from the current Open-Rosalind build on `mvp4`.

- Sample date: 2026-05-07 UTC
- Main endpoint: `POST /api/chat`
- Backend observed from `/api/health`: `openrouter`, model `google/gemma-4-26b-a4b-it`

## 1. What is BRCA1?

- Session: `20260507-190312-7b0a6a`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Resolved to human BRCA1, UniProt `P38398`
  - Summary identified BRCA1 as an E3 ubiquitin-protein ligase with central DNA-repair roles

## 2. What is TP53?

- Session: `20260507-190330-965c96`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Resolved to human TP53, UniProt `P04637`
  - Summary described p53 as a tumor suppressor transcription factor

## 3. P04637

- Session: `20260507-190422-20db19`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Direct accession lookup succeeded for UniProt `P04637`
  - Summary identified the protein as human cellular tumor antigen p53

## 4. Find recent papers about CRISPR base editing in 2024

- Session: `20260507-190603-af4177`
- Mode: `single_step`
- Skill: `literature_search`
- Result:
  - Query used: `(CRISPR base editing) AND 2024[dp]`
  - Top PMIDs: `38308006`, `38786024`, `38661449`

## 5. Find recent papers about glioblastoma immunotherapy

- Session: `20260507-190612-5f7579`
- Mode: `single_step`
- Skill: `literature_search`
- Result:
  - Query used: `glioblastoma immunotherapy`
  - Top PMIDs: `39406966`, `29643471`, `40847231`

## 6. What is the effect of TP53 p.R175H mutation?

- Session: `20260507-190623-35c4f2`
- Mode: `single_step`
- Skill: `mutation_effect`
- Result:
  - Resolved `TP53` to UniProt `P04637`
  - Assessment: `possibly impactful`
  - Notable flag: `aromatic gain/loss`

## 7. What is the effect of BRAF V600E mutation?

- Session: `20260507-190645-73a4ec`
- Mode: `single_step`
- Skill: `mutation_effect`
- Result:
  - Resolved `BRAF` to UniProt `P15056`
  - Assessment: `possibly impactful`

## 8. Analyze sequence ATGAAACGT

- Session: `20260507-190653-58f302`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - No sequence analysis workflow was triggered
  - Returned no UniProt matches

## 9. Analyze sequence MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD

- Session: `20260507-190656-51d194`
- Mode: `single_step`
- Skill: `sequence_basic_analysis`
- Result:
  - Classified as a protein sequence of length `393`
  - Summary highlighted high proline and serine content

## 10. Analyze sequence MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPSQAMDDLMLSPDDIEQWFTEDPGPDEAPRMPEAAPPVAPAPAAPTPAAPAPAPSWPLSSSVPSQKTYQGSYGFRLGFLHSGTAKSVTCTYSPALNKMFCQLAKTCPVQLWVDSTPPPGTRVRAMAIYKQSQHMTEVVRRCPHHERCSDSDGLAPPQHLIRVEGNLRVEYLDDRNTFRHSVVVPYEPPEVGSDCTTIHYNYMCNSSCMGGMNRRPILTIITLEDSSGNLLGRNSFEVRVCACPGRDRRTEEENLRKKGEPHHELPPGSTKRALPNNTSSSPQPKKKPLDGEYFTLQIRGRERFEMFRELNEALELKDAQAGKEPGGSRAHSSHLKSKKGQSTSRHKKLMFKTEGPDSD and find papers

- Session: `task_20260507_190712_5747`
- Mode: `harness`
- Skill: `harness`
- Result:
  - Step 1 used `workflow_protein_annotation`
  - Step 2 used `literature_search`
  - Final report said `2/2 successful steps`, but both step summaries were no-hit style outcomes

## 11. Analyze sequence MVKVGVNGFGRIGRLVTRA and find similar proteins

- Session: `task_20260507_190720_5797`
- Mode: `harness`
- Skill: `harness`
- Result:
  - Step 1 used `workflow_protein_annotation`
  - Step 2 used `uniprot_lookup`
  - No BLAST-style homology hit was returned

## 12. What is EGFR?

- Session: `20260507-191329-e60871`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Resolved to human EGFR, UniProt `P00533`
  - Summary described EGFR as a receptor tyrosine kinase

## 13. Find papers about TP53 apoptosis

- Session: `20260507-191355-8e04fd`
- Mode: `single_step`
- Skill: `literature_search`
- Result:
  - Query used: `TP53 apoptosis`
  - Top PMIDs: `39909041`, `41135852`, `38729160`

## 14. What is the effect of EGFR L858R mutation?

- Session: `20260507-191434-4bd7f4`
- Mode: `single_step`
- Skill: `mutation_effect`
- Result:
  - Resolved `EGFR` to UniProt `P00533`
  - Assessment: `possibly impactful`

## 15. Analyze sequence AUGGCUACGGAU

- Session: `20260507-191441-26c2d8`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - No RNA-aware sequence workflow was triggered
  - Returned no UniProt matches

## 16. What is BRCA1 and find papers

- Session: `task_20260507_191516_8124`
- Mode: `harness`
- Skill: `harness`
- Result:
  - Planner selected `workflow_mutation_assessment`
  - The step reported missing input data

## 17. Analyze sequence ATGAAACGT and find papers

- Session: `task_20260507_191524_4775`
- Mode: `harness`
- Skill: `harness`
- Result:
  - Step 1 reported the sequence as empty
  - Step 2 searched a generic query and returned PubMed hits

## 18. What is KRAS?

- Session: `20260507-191706-0abf57`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Resolved to human KRAS, UniProt `P01116`

## 19. What is insulin?

- Session: `20260507-191747-2dc703`
- Mode: `single_step`
- Skill: `uniprot_lookup`
- Result:
  - Resolved to human insulin, UniProt `P01308`

## 20. Find recent papers about single-cell atlas lung cancer

- Session: `20260507-191756-a50d64`
- Mode: `single_step`
- Skill: `literature_search`
- Result:
  - Query used: `single-cell atlas lung cancer`
  - Top PMIDs: `36368318`, `40147443`, `37248301`

## Observations

- Gene and accession lookup are working for common proteins such as BRCA1 and TP53.
- Literature search is working and returns grounded PMIDs.
- Rule-based mutation assessment is working for common named variants.
- Some sequence prompts still route in ways that are not ideal.
- Some harness multi-step prompts still plan or propagate inputs incorrectly.
