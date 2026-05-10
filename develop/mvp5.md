# MVP5: Local BioDB Layer

Goal: move the highest-value bio lookups to a local-first database layer while keeping public API shapes stable.

## Scope

- Add a local SQLite-backed bio database with manifest, versioning, and provenance.
- Seed a minimal UniProt mirror for the highest-frequency demo/test targets first.
- Make `uniprot.search` and `uniprot.fetch` prefer local data, then fall back to the public API.
- Keep returned payload shapes compatible with existing tool and skill outputs.
- Add CLI commands to inspect and refresh the local database.

## Initial Seed

- `BRCA1 / P38398`
- `TP53 / P04637`
- `INS / P01308`
- `HBB / P68871`
- `HBA1/HBA2 / P69905`

## Non-goals

- Full UniProt mirroring.
- Full PubMed indexing.
- Local BLAST or DIAMOND infrastructure.
- Changing harness routing or skill evidence contracts.

## Acceptance

- `uniprot.search("BRCA1")` resolves from the local DB without needing the remote API.
- `uniprot.fetch("P38398")` resolves from the local DB with the same output shape as the public tool.
- Offline mode still answers seeded queries.
- Existing skills continue to receive structured evidence and trace.
