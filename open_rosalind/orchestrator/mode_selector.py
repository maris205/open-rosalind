"""Auto execution mode selector.

First-level route:
- model_only: answer from the language model itself, clearly labeled as no-tool.
- single_step: use one constrained skill/tool workflow.
- harness: use the multi-step harness.
"""
from __future__ import annotations

import re

# Phrases that strongly suggest multi-step execution
HARNESS_KEYWORDS = [
    r"\band\s+find\s+(papers|literature|articles)",
    r"\band\s+look\s+up",
    r"\band\s+search\s+(for|the)",
    r"\bthen\s+(find|look|search|get)",
    r"\bafter\s+that",
    r"\bsubsequently",
    r"\balso\s+(find|search|look|get)",
    r"\bcompare\s+.+\s+(to|with|against)",
    r"\bassess\s+.+\s+(impact|effect)",
]

# Phrases that suggest research workflows
RESEARCH_PATTERNS = [
    r"analyze.+find.+papers",
    r"identify.+literature",
    r"workflow",
    r"pipeline",
    r"protein.+structure.+function",
]

BASIC_BIO_ABBREVIATIONS = {
    "DNA", "RNA", "PCR", "mRNA", "tRNA", "rRNA",
    "CRISPR", "ATP", "ADP", "NADH", "GO", "COVID",
    "AI", "LLM", "MCP",
}

ASCII_TOKEN_RE = r"(?<![A-Za-z0-9]){}(?![A-Za-z0-9])"


def _uppercase_entity_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(ASCII_TOKEN_RE.format(r"[A-Z][A-Z0-9]{1,7}"), text)
        if token not in BASIC_BIO_ABBREVIATIONS and (any(ch.isdigit() for ch in token) or len(token) <= 5)
    ]


def should_use_tools(user_input: str) -> bool:
    """Return True only for requests that should use scientific tools/skills.

    Routing contract:
    - Call skills for concrete, checkable scientific operations: named
      gene/protein/accession lookup, sequence computation, mutation/variant
      assessment, literature search, or specific database-backed evidence.
    - Do not call skills for product/help/chat questions or broad educational
      explanations without a concrete target.
    """
    text = (user_input or "").strip()
    if not text:
        return False
    lowered = text.lower()

    if _uppercase_entity_tokens(text):  # BRCA1, TP53, EGFR
        return True
    if re.search(ASCII_TOKEN_RE.format(r"[OPQ][0-9][A-Z0-9]{3}[0-9]"), text):
        return True
    if re.search(ASCII_TOKEN_RE.format(r"(?:p\.)?[A-Z]\d{1,4}[A-Z\*]"), text):
        return True
    if re.search(r"\b(?:wt|wild[-\s]*type)\s*[:=]|\b(?:mt|mutant)\s*[:=]", lowered):
        return True
    if re.search(r"\b(mutation|mutant|variant|substitution|polymorphism|allele)\b", lowered):
        return True
    if re.search(r"\b(?:paper|papers|literature|pubmed|cite|citation|publication|publications)\b", lowered):
        return True
    if re.search(r"\b(?:uniprot|ncbi|clinvar|gnomad|pubchem|chembl|pdb|rcsb|reactome|string|biogrid|blast)\b", lowered):
        return True
    if re.search(r"\b(?:sequence|fasta|protein sequence|gc|reverse[-\s]*complement|revcomp|blast|similar proteins?|homolog|homology|alignment?)\b", lowered):
        return True
    if re.search(r"\btranslate\b", lowered) and re.search(r"\b(dna|rna|sequence|codon|nucleotide)\b", lowered):
        return True
    if re.search(r"(查询|检索|搜索).*(文献|论文|数据库|uniprot|ncbi|clinvar|gnomad|pdb|pubmed|通路|结构|药物)", lowered):
        return True
    if re.search(r"(分析|评估|比对|注释).*(突变|变异|序列|文献|论文|通路|结构|药物)", text):
        return True
    if re.search(r"(这个|该|this)\s*(蛋白|基因|protein|gene|variant|mutation)", lowered):
        return True
    if re.search(r"[ACGTUNacgtun]{12,}", text):
        return True
    if re.search(r"[ACDEFGHIKLMNPQRSTVWYBXZ\*]{20,}", text):
        return True
    return False


def should_use_model_only(user_input: str) -> bool:
    """Return True for any prompt that does not need scientific tools."""
    return not should_use_tools(user_input)


def select_mode(user_input: str) -> tuple[str, str]:
    """
    Auto-select execution mode based on user input.

    Returns:
        (mode, reason) where:
            mode: "model_only" | "single_step" | "harness"
            reason: human-readable explanation
    """
    text = user_input.lower().strip()

    if should_use_model_only(user_input):
        return "model_only", "model-only route: general/help/basic concept question; no external tools used"

    # Check for explicit harness keywords
    for pattern in HARNESS_KEYWORDS:
        if re.search(pattern, text):
            return "harness", f"detected multi-step intent: matches /{pattern}/"

    # Check for research workflow patterns
    for pattern in RESEARCH_PATTERNS:
        if re.search(pattern, text):
            return "harness", f"detected research workflow: /{pattern}/"

    # Long inputs with multiple verbs suggest multi-step
    verb_count = sum(1 for kw in ["analyze", "find", "search", "look", "compare", "identify", "summarize"]
                     if kw in text)
    if verb_count >= 2:
        return "harness", f"multiple action verbs ({verb_count}) suggest multi-step task"

    # Default: single step
    return "single_step", "single skill suffices"
