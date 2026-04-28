"""Mutation effect handler."""
from . import tools

def handler(payload: dict, trace) -> dict:
    wt = payload.get("wt", "").strip()
    mt = payload.get("mt", "").strip()
    
    if not wt or not mt:
        return {"annotation": {"kind": "mutation"}, "confidence": 0.0, "notes": ["Missing WT or MT"], "mutation": {}}
    
    diff = tools.diff(wt=wt, mt=mt)
    
    return {
        "annotation": {"kind": "mutation", "n_differences": diff["n_differences"], "severity": diff["severity"]},
        "confidence": 0.75 if diff["n_differences"] >= 0 else 0.0,
        "notes": [],
        "mutation": diff,
    }
