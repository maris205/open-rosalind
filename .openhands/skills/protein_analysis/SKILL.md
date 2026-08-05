---
name: protein_analysis
description: Evidence-aware protein sequence and annotation analysis inspired by the main product protein workflow.
---

# Protein Analysis

Accept a protein sequence, UniProt accession, gene symbol, or protein name. First identify the input type and organism if supplied.

Structure the response as:

1. Input interpretation and validation.
2. Sequence-level observations that can be derived from supplied data.
3. Protein identity and annotation evidence.
4. Function, domains, localization, structure, interactions, and homologs.
5. Confidence, missing evidence, and recommended database or tool checks.

Never invent UniProt, PDB, InterPro, AlphaFold, BLAST, or other database results. If no actual tool output is present, describe the query plan and mark database-dependent statements as unverified. Do not infer function from a short sequence alone.
