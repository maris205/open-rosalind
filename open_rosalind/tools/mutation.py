"""Minimal mutation effect heuristics — no external DB, no model.

Designed for MVP1 Demo 2: take wild-type and mutant protein sequences (or
HGVS-style point mutations like "p.R175H"), highlight differences, and apply
simple physico-chemical rules to flag potentially impactful changes.

This is intentionally a *rule-based* baseline. It is NOT a substitute for
PolyPhen/AlphaMissense/SIFT — it just gives the LLM something concrete to
explain, and a structured evidence object the trace can record.
"""
from __future__ import annotations

import re
from typing import Any

from .base import ToolSpec

_HYDROPHOBIC = set("AVILMFWY")
_POLAR_UNCHARGED = set("STNQCG")
_POSITIVE = set("KRH")
_NEGATIVE = set("DE")
_AROMATIC = set("FWYH")
_TINY = set("AGSCP")


def _class_of(aa: str) -> str:
    if aa in _POSITIVE:
        return "positive"
    if aa in _NEGATIVE:
        return "negative"
    if aa in _HYDROPHOBIC:
        return "hydrophobic"
    if aa in _POLAR_UNCHARGED:
        return "polar_uncharged"
    return "other"


_HGVS_RE = re.compile(r"^(?:p\.)?([A-Z])(\d+)([A-Z\*])$", re.IGNORECASE)


def _apply_hgvs(seq: str, hgvs: str) -> tuple[str, list[dict]]:
    """Apply a single point mutation in HGVS-ish form to a wild-type sequence."""
    m = _HGVS_RE.match(hgvs.strip())
    if not m:
        raise ValueError(f"Could not parse mutation: {hgvs!r}. Expected e.g. p.R175H or R175H.")
    wt, pos_s, mt = m.group(1).upper(), m.group(2), m.group(3).upper()
    pos = int(pos_s)
    if pos < 1 or pos > len(seq):
        raise ValueError(f"Position {pos} out of range 1..{len(seq)}")
    actual = seq[pos - 1].upper()
    if actual != wt:
        raise ValueError(f"Position {pos} in WT is '{actual}', but mutation expects '{wt}'.")
    mut = seq[: pos - 1] + mt + seq[pos:]
    return mut, [{"position": pos, "wt": wt, "mt": mt}]


def _diff(wt: str, mt: str) -> list[dict]:
    diffs = []
    n = min(len(wt), len(mt))
    for i in range(n):
        if wt[i].upper() != mt[i].upper():
            diffs.append({"position": i + 1, "wt": wt[i].upper(), "mt": mt[i].upper()})
    if len(wt) != len(mt):
        diffs.append({
            "position": n + 1,
            "wt": wt[n:].upper() or "-",
            "mt": mt[n:].upper() or "-",
            "indel": True,
        })
    return diffs


def _annotate(diff: dict) -> dict:
    if diff.get("indel"):
        return {**diff, "category": "indel", "flags": ["length-changing"]}
    wt, mt = diff["wt"], diff["mt"]
    flags = []
    if mt == "*":
        flags.append("introduces stop codon (truncation)")
    if _class_of(wt) != _class_of(mt):
        flags.append(f"class change: {_class_of(wt)} → {_class_of(mt)}")
    if (wt in _POSITIVE and mt in _NEGATIVE) or (wt in _NEGATIVE and mt in _POSITIVE):
        flags.append("charge reversal")
    if wt == "P" or mt == "P":
        flags.append("proline involved (backbone geometry)")
    if wt == "G" or mt == "G":
        flags.append("glycine involved (flexibility)")
    if (wt == "C") ^ (mt == "C"):
        flags.append("cysteine gain/loss (disulfide bond)")
    if (wt in _AROMATIC) ^ (mt in _AROMATIC):
        flags.append("aromatic gain/loss")
    severity = "low"
    if any("stop" in f or "charge reversal" in f or "disulfide" in f for f in flags):
        severity = "high"
    elif flags:
        severity = "medium"
    return {**diff, "category": "missense", "flags": flags, "severity": severity}


def diff_sequences(wild_type: str, mutant: str | None = None, mutation: str | None = None) -> dict[str, Any]:
    wt = re.sub(r"\s+", "", wild_type).upper()
    if mutant:
        mt = re.sub(r"\s+", "", mutant).upper()
        diffs = _diff(wt, mt)
    elif mutation:
        mt, diffs = _apply_hgvs(wt, mutation)
    else:
        raise ValueError("Provide either `mutant` sequence or `mutation` (e.g. p.R175H).")

    annotated = [_annotate(d) for d in diffs]
    has_high = any(d.get("severity") == "high" for d in annotated)
    has_medium = any(d.get("severity") == "medium" for d in annotated)
    overall = "likely impactful" if has_high else ("possibly impactful" if has_medium else "likely benign")
    return {
        "wt_length": len(wt),
        "mt_length": len(mt),
        "n_differences": len(annotated),
        "differences": annotated,
        "overall_assessment": overall,
        "disclaimer": "Rule-based heuristic only — not a substitute for PolyPhen/SIFT/AlphaMissense.",
    }


DIFF_SPEC = ToolSpec(
    name="mutation.diff",
    description="Compare wild-type vs mutant protein sequence (or apply an HGVS-style point mutation like p.R175H) and annotate each difference with a simple physico-chemical impact heuristic.",
    input_schema={
        "type": "object",
        "properties": {
            "wild_type": {"type": "string"},
            "mutant": {"type": "string"},
            "mutation": {"type": "string"},
        },
        "required": ["wild_type"],
    },
    output_schema={"type": "object"},
    handler=diff_sequences,
)
