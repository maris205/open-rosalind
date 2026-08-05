---
name: mutation_assessment
description: Assess sequence variants with explicit separation of computed differences, inference, database evidence, and clinical interpretation.
---

# Mutation Assessment

Accept WT/MT sequences, a gene symbol plus HGVS variant, or a structured variant record.

Structure the response as:

1. Normalized input and ambiguities.
2. Direct sequence difference, if derivable from supplied sequences.
3. Amino-acid or nucleotide property change.
4. Protein and domain context.
5. Population, functional, clinical, and literature evidence needed.
6. Overall evidence summary and next verification steps.

Do not label a variant pathogenic, benign, actionable, or clinically significant without appropriate evidence. Never fabricate ClinVar, gnomAD, UniProt, CIViC, ACMG, PMID, or DOI records. A biochemical property change is not by itself evidence of pathogenicity.
