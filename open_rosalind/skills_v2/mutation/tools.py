"""Mutation analysis tools."""

def diff(wt: str, mt: str) -> dict:
    """Compare WT and MT sequences."""
    wt = wt.upper().strip()
    mt = mt.upper().strip()
    
    if len(wt) != len(mt):
        return {"n_differences": -1, "positions": [], "changes": [], "severity": "unknown"}
    
    positions = []
    changes = []
    for i, (w, m) in enumerate(zip(wt, mt)):
        if w != m:
            positions.append(i)
            changes.append(f"{w}→{m}")
    
    severity = "none" if not changes else ("high" if len(changes) > 3 else "moderate")
    
    return {"n_differences": len(changes), "positions": positions, "changes": changes, "severity": severity}
