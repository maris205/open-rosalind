---
name: reference-verification
description: Use when checking whether bibliography entries, DOI, PMID, titles, journals, authors, and years are real and internally consistent.
---
# Reference Verification Skill

Use this skill when references must be screened for hallucination, metadata mismatch, or missing identifiers.

## Purpose

Reduce fabricated-reference risk by checking reference existence and metadata consistency before the Agent uses citations in reports or manuscripts.

## Output Structure

1. Verification summary
2. Per-reference status
3. DOI / PMID / title / year consistency
4. Candidate matches
5. Fabrication-risk items
6. Manual verification checklist

## Rules

- Prefer deterministic lookup results over model guesses.
- Never create a DOI, PMID, URL, author list, journal name, or publication year.
- Distinguish `Verified`, `Metadata Mismatch`, `Candidate Match`, `Unverified`, and `Fabrication Risk`.
- A real reference does not automatically support a manuscript claim.
- High-risk claims still require reading the original source.