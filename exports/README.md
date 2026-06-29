# Exports

This directory is reserved for generated Markdown and DOCX exports.

Recommended workflow:

1. Ask Open-Rosalind Edu to produce structured Markdown.
2. Save the answer as `exports/output.md`.
3. Convert it to DOCX with:

```bash
python scripts/md_to_docx.py exports/output.md exports/output.docx
```

Generated files are drafts and must be manually reviewed before academic submission.
