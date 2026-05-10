---
name: model_only
description: Route non-tool questions to the language model with explicit no-tool labeling.
category: meta
tools_used: []
---

# Model-Only Answer

Use this skill only after first-level routing determines that the user is not
asking for a concrete scientific lookup or computation.

Appropriate questions include:

- Product/help questions such as "What can you do?" or "你有什么功能".
- Conversational identity questions such as "Who are you?" or "你是谁".
- Basic educational explanations such as "Explain the central dogma".
- General non-biology questions where Open-Rosalind has no connected external
  tool, such as realtime weather.

Do not use this skill for concrete biological facts that should be grounded in
tools, including gene/protein lookup, sequence analysis, mutation assessment,
literature search, database queries, similarity search, pathways, structures,
clinical evidence, or compound/target lookup.

Outputs must state that no external scientific tools or database evidence were
used. If the user actually needs database-backed evidence, route to the relevant
scientific skill instead.

Hybrid fallback rule:

- If a scientific skill was selected but returns no usable evidence or
  confidence `0.0`, Open-Rosalind may append a clearly labeled model-only
  fallback.
- That fallback is user-facing guidance only. It must not be treated as
  scientific evidence, and it must not replace the original skill evidence,
  confidence, or trace.
