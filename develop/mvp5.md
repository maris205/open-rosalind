# MVP5: Local BioDB Layer

Goal: move the highest-value bio lookups to a local-first database layer while keeping public API shapes stable.

## Scope

- Add a local SQLite-backed bio database with manifest, versioning, and provenance.
- Seed a minimal multi-source mirror for the highest-frequency demo/test targets first.
- Make UniProt, PubMed, NCBI Gene, and Ensembl lookups prefer local data, then fall back to public APIs.
- Keep returned payload shapes compatible with existing tool and skill outputs.
- Add CLI commands to inspect and refresh the local database.

## Initial Seed

- `BRCA1 / P38398`
- `TP53 / P04637`
- `INS / P01308`
- `HBB / P68871`
- `HBA1/HBA2 / P69905`
- PubMed seed papers for BRCA1, TP53, INS, HBB, and alpha-globin/thalassemia topics.
- NCBI Gene seed records for BRCA1, TP53, INS, HBB, HBA1, and HBA2.
- Ensembl gene and cross-reference seed records for BRCA1, TP53, INS, HBB, HBA1, and HBA2.

## Non-goals

- Full UniProt mirroring.
- Full PubMed indexing.
- Local BLAST or DIAMOND infrastructure.
- Changing harness routing or skill evidence contracts.

## Acceptance

- `uniprot.search("BRCA1")` resolves from the local DB without needing the remote API.
- `uniprot.fetch("P38398")` resolves from the local DB with the same output shape as the public tool.
- `pubmed.search("BRCA1 DNA repair")` resolves seeded literature locally.
- `ncbi_gene.search_gene("TP53")` and `ensembl.lookup_gene("TP53")` resolve seeded gene identifiers locally.
- Offline mode still answers seeded queries.
- Existing skills continue to receive structured evidence and trace.
