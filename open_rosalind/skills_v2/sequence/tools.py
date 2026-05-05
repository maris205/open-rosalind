"""Sequence analysis tools (local computation)."""
from __future__ import annotations

from ...tools import sequence as base_sequence
from .helpers import (
    align_pairwise as _align_pairwise_helper,
    detect_type as _detect_type_helper,
    gc_content as _gc_content_helper,
    kmer_stats as _kmer_stats_helper,
    protein_basic_stats as _protein_basic_stats_helper,
    reverse_complement as _reverse_complement_helper,
    translate as _translate_helper,
)

def analyze(sequence: str) -> dict:
    """Analyze DNA/RNA/protein sequence using the shared tool implementation."""
    result = base_sequence.analyze(sequence)
    return {
        "records": result["records"],
        "n_records": result["total_records"],
    }


def detect_type(sequence: str) -> dict:
    return _detect_type_helper(sequence)


def gc_content(sequence: str) -> dict:
    return _gc_content_helper(sequence)


def translate(sequence: str) -> dict:
    return _translate_helper(sequence)


def reverse_complement(sequence: str) -> dict:
    return _reverse_complement_helper(sequence)


def kmer_stats(sequence: str, k: int = 3, top_n: int = 10) -> dict:
    return _kmer_stats_helper(sequence, k=k, top_n=top_n)


def protein_basic_stats(sequence: str) -> dict:
    return _protein_basic_stats_helper(sequence)


def align_pairwise(sequence_a: str, sequence_b: str, mode: str = "global") -> dict:
    return _align_pairwise_helper(sequence_a=sequence_a, sequence_b=sequence_b, mode=mode)
