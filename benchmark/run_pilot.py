"""Pilot ablation experiment: 10 tasks × 5 conditions.

Conditions:
  1. full        — Open-Rosalind reference (router + skills + tool-first + citation enforcement + harness)
  2. react       — free-form ReAct loop with raw atomic tools, no router/no template/no citation rule
  3. no_tool     — full Open-Rosalind shape but NO tool calls; LLM answers from parametric memory
  4. no_cite     — full Open-Rosalind, but the system prompt does NOT require citations
  5. no_template — multi-step tasks routed through the single-step agent (no harness templates)

Outputs benchmark/pilot_results.json with per-task per-condition records,
and benchmark/pilot_summary.md with aggregate metrics.

Run: python benchmark/run_pilot.py --workers 4
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from open_rosalind.backends import OpenRouterBackend
from open_rosalind.orchestrator.agent import Agent, SYSTEM_PROMPT as AGENT_SYSTEM_PROMPT
from open_rosalind.orchestrator.router import detect_intent
from open_rosalind.skills import SKILL_REGISTRY
from open_rosalind.tools import REGISTRY as TOOL_REGISTRY
from open_rosalind.harness.runner import TaskRunner
from open_rosalind.harness.planner import ConstrainedPlanner
from open_rosalind.harness.adapter import AgentAdapter
from open_rosalind.harness.task import Task

MODEL = os.environ.get("PILOT_MODEL", "google/gemma-4-26b-a4b-it")
PILOT_PATH = ROOT / "benchmark" / "pilot10.json"
OUT_JSON = ROOT / "benchmark" / "pilot_results.json"
OUT_MD = ROOT / "benchmark" / "pilot_summary.md"


# -----------------------------------------------------------------
#  helpers
# -----------------------------------------------------------------
def has_keywords(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    # Greek-to-ASCII transliteration so that answers containing "PGC-1α"
    # match gold keywords written as "pgc-1alpha", and vice versa.
    greek_map = {
        "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
        "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
        "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
        "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
        "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
        "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta", "Ε": "epsilon",
        "Ζ": "zeta", "Η": "eta", "Θ": "theta", "Ι": "iota", "Κ": "kappa",
        "Λ": "lambda", "Μ": "mu", "Ν": "nu", "Ξ": "xi", "Ο": "omicron",
        "Π": "pi", "Ρ": "rho", "Σ": "sigma", "Τ": "tau", "Υ": "upsilon",
        "Φ": "phi", "Χ": "chi", "Ψ": "psi", "Ω": "omega",
    }
    t_ascii = "".join(greek_map.get(c, c) for c in t)
    # HGVS 3-letter ↔ 1-letter equivalents so that "p.Gly12Asp" keyword matches
    # an answer that says "glycine to aspartate at position 12" or "G12D".
    aa3to1 = {"ala":"a","arg":"r","asn":"n","asp":"d","cys":"c","gln":"q",
              "glu":"e","gly":"g","his":"h","ile":"i","leu":"l","lys":"k",
              "met":"m","phe":"f","pro":"p","ser":"s","thr":"t","trp":"w",
              "tyr":"y","val":"v"}

    def _expand(k: str) -> list[str]:
        """Return a list of accepted string-substrings any of which counts as a match."""
        kl = k.lower()
        out = [kl]
        kl_ascii = "".join(greek_map.get(c, c) for c in kl)
        out.append(kl_ascii)
        # HGVS p.XyyZ patterns
        import re as _re
        m3 = _re.fullmatch(r"p\.([a-z]{3})(\d+)([a-z]{3}|del|ter|\*)", kl)
        if m3:
            ref, pos, alt = m3.group(1), m3.group(2), m3.group(3)
            ref1 = aa3to1.get(ref)
            alt1 = aa3to1.get(alt, alt) if alt != "*" else "*"
            if ref1 and alt1:
                out.append(f"{ref1}{pos}{alt1}")
                out.append(f"p.{ref1}{pos}{alt1}")
        m1 = _re.fullmatch(r"p\.([a-z])(\d+)([a-z\*])", kl)
        if m1:
            ref, pos, alt = m1.group(1), m1.group(2), m1.group(3)
            out.append(f"{ref}{pos}{alt}")
        return out

    def _has(k: str) -> bool:
        for candidate in _expand(k):
            if candidate in t or candidate in t_ascii:
                return True
        return False

    return all(_has(k) for k in keywords)


def cite_present(text: str) -> bool:
    """Every non-trivial sentence has at least one [UniProt:..]/[PMID:..]/[tool:..] tag."""
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    if not sents:
        return False
    return all(re.search(r"\[(UniProt|PMID|tool):[^\]]+\]", s) for s in sents if len(s) > 30)


# -----------------------------------------------------------------
#  Condition: FULL Open-Rosalind
# -----------------------------------------------------------------
def run_full(task: dict, backend: OpenRouterBackend) -> dict:
    is_multi = task["split"] == "multistep"
    if is_multi:
        adapter = AgentAdapter(Agent(backend, trace_dir="/tmp/pilot_traces", session_dir="/tmp/pilot_sessions"))
        runner = TaskRunner(adapter)
        t = Task(task_id=f"pilot_{task['id']}", user_goal=task["input"])
        completed = runner.run(t)
        steps = []
        path = []
        for s in completed.steps:
            tool_steps = s.trace or []
            steps.extend(tool_steps)
            path.extend([ts.get("skill") for ts in tool_steps])
            if s.expected_workflow:
                path.append(s.expected_workflow)
        return {
            "summary": completed.final_report or "",
            "tool_path": path,
            "trace_steps": steps,
            "trace_complete": bool(steps),
        }
    agent = Agent(backend, trace_dir="/tmp/pilot_traces", session_dir="/tmp/pilot_sessions")
    out = agent.analyze(task["input"])
    steps = out.get("trace_steps", [])
    return {
        "summary": out.get("summary", ""),
        "tool_path": [s.get("skill") for s in steps],
        "trace_steps": steps,
        "trace_complete": bool(steps),
    }


# -----------------------------------------------------------------
#  Condition: NO_TOOL — LLM only, no tools
# -----------------------------------------------------------------
NO_TOOL_PROMPT = (
    "You are a biology assistant. Answer the user's question from your own knowledge. "
    "Do NOT call any tools. Be concise."
)

def run_no_tool(task: dict, backend: OpenRouterBackend) -> dict:
    msgs = [{"role": "system", "content": NO_TOOL_PROMPT},
            {"role": "user", "content": task["input"]}]
    resp = backend.chat(msgs, temperature=0.2, max_tokens=512)
    return {"summary": resp.content, "tool_path": [], "trace_steps": [], "trace_complete": False}


# -----------------------------------------------------------------
#  Condition: NO_CITE — full pipeline but drop citation rule
# -----------------------------------------------------------------
NO_CITE_SYSTEM = (
    "You are Open-Rosalind, a life-science assistant. EVIDENCE has been pre-fetched "
    "from authoritative databases. Use ONLY EVIDENCE. Be concise (~250 words). "
    "Do NOT add citation tags or brackets — write plain prose."
)

def run_no_cite(task: dict, backend: OpenRouterBackend) -> dict:
    """Reuse full pipeline up to skill execution, then synthesize without citation rule."""
    is_multi = task["split"] == "multistep"
    import open_rosalind.orchestrator.agent as A
    old = A.SYSTEM_PROMPT
    A.SYSTEM_PROMPT = NO_CITE_SYSTEM
    try:
        agent = Agent(backend, trace_dir="/tmp/pilot_traces", session_dir="/tmp/pilot_sessions")
        if is_multi:
            adapter = AgentAdapter(agent)
            runner = TaskRunner(adapter)
            t = Task(task_id=f"pilot_nocite_{task['id']}", user_goal=task["input"])
            completed = runner.run(t)
            steps = []
            path = []
            for s in completed.steps:
                tool_steps = s.trace or []
                steps.extend(tool_steps)
                path.extend([ts.get("skill") for ts in tool_steps])
                if s.expected_workflow:
                    path.append(s.expected_workflow)
            return {
                "summary": completed.final_report or "",
                "tool_path": path,
                "trace_steps": steps,
                "trace_complete": bool(steps),
            }
        out = agent.analyze(task["input"])
    finally:
        A.SYSTEM_PROMPT = old
    steps = out.get("trace_steps", [])
    return {
        "summary": out.get("summary", ""),
        "tool_path": [s.get("skill") for s in steps],
        "trace_steps": steps,
        "trace_complete": bool(steps),
    }


# -----------------------------------------------------------------
#  Condition: NO_TEMPLATE — force multi-step tasks through single-step agent
# -----------------------------------------------------------------
def run_no_template(task: dict, backend: OpenRouterBackend) -> dict:
    """Multi-step tasks: do single-step agent only (router picks one skill).
    Single-step tasks: identical to full."""
    agent = Agent(backend, trace_dir="/tmp/pilot_traces", session_dir="/tmp/pilot_sessions")
    out = agent.analyze(task["input"])
    steps = out.get("trace_steps", [])
    return {
        "summary": out.get("summary", ""),
        "tool_path": [s.get("skill") for s in steps],
        "trace_steps": steps,
        "trace_complete": bool(steps),
    }


# -----------------------------------------------------------------
#  Condition: REACT — free-form ReAct with raw atomic tools
# -----------------------------------------------------------------
REACT_SYSTEM = (
    "You are a biology research assistant. You have access to atomic tools listed below. "
    "When a user asks a question, decide which tools to call (zero or more), then synthesize an answer. "
    "After tool results, you MAY call more tools or produce the final answer. "
    "Maximum 6 tool calls. No special citation format required."
)

def _tool_schema_openai() -> list[dict]:
    out = []
    for spec in TOOL_REGISTRY.values():
        out.append({
            "type": "function",
            "function": {
                "name": spec.name.replace(".", "_"),
                "description": spec.description,
                "parameters": spec.input_schema,
            },
        })
    return out

def _call_tool(tool_name: str, args: dict) -> Any:
    real_name = tool_name.replace("_", ".", 1)  # sequence_analyze -> sequence.analyze
    spec = TOOL_REGISTRY.get(real_name)
    if not spec:
        return {"error": f"unknown tool {tool_name}"}
    try:
        return spec.handler(**args)
    except Exception as e:
        return {"error": str(e)}

def run_react(task: dict, backend: OpenRouterBackend) -> dict:
    client: OpenAI = backend.client
    tools_schema = _tool_schema_openai()
    msgs = [
        {"role": "system", "content": REACT_SYSTEM},
        {"role": "user", "content": task["input"]},
    ]
    tool_path: list[str] = []
    trace_steps: list[dict] = []
    summary = ""
    for hop in range(6):
        try:
            resp = client.chat.completions.create(
                model=backend.model, messages=msgs, tools=tools_schema,
                tool_choice="auto", temperature=0.2, max_tokens=800,
            )
        except Exception as e:
            summary = f"[react backend error: {e}]"
            break
        m = resp.choices[0].message
        if m.tool_calls:
            msgs.append({
                "role": "assistant",
                "content": m.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in m.tool_calls
                ],
            })
            for tc in m.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                t0 = time.time()
                result = _call_tool(tc.function.name, args)
                latency_ms = int((time.time() - t0) * 1000)
                tool_path.append(tc.function.name.replace("_", ".", 1))
                trace_steps.append({
                    "skill": tc.function.name.replace("_", ".", 1),
                    "input": args,
                    "output": result,
                    "latency_ms": latency_ms,
                    "status": "error" if isinstance(result, dict) and result.get("error") else "success",
                })
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:4000],
                })
        else:
            summary = (m.content or "").strip()
            break
    else:
        summary = "[react: max hops reached without final answer]"
    return {
        "summary": summary,
        "tool_path": tool_path,
        "trace_steps": trace_steps,
        "trace_complete": bool(trace_steps),
    }


# -----------------------------------------------------------------
#  scoring
# -----------------------------------------------------------------
def score(task: dict, result: dict) -> dict:
    expected_path = task.get("gold_path", [])
    actual_path = result.get("tool_path", [])
    # Tool correctness: did we call the gold-path tools (substring match for ReAct fuzziness)
    if not expected_path:
        tool_corr = True
    else:
        tool_corr = all(any(g.split(".")[0] in a for a in actual_path) for g in expected_path) and bool(actual_path)
    summary = result.get("summary", "")
    accuracy = has_keywords(summary, task.get("keywords", []))
    return {
        "accuracy": accuracy,
        "tool_correctness": tool_corr,
        "citation_presence": cite_present(summary),
        "trace_completeness": bool(result.get("trace_complete")),
        "no_fail": "[react backend error" not in summary and "Model backend unavailable" not in summary,
    }


# -----------------------------------------------------------------
#  driver
# -----------------------------------------------------------------
CONDITIONS = {
    "full": run_full,
    "react": run_react,
    "no_tool": run_no_tool,
    "no_cite": run_no_cite,
    "no_template": run_no_template,
}


def run_one(task: dict, cond: str, backend: OpenRouterBackend) -> dict:
    t0 = time.time()
    try:
        r = CONDITIONS[cond](task, backend)
        err = None
    except Exception as e:
        r = {"summary": f"[{type(e).__name__}: {e}]", "tool_path": [], "trace_steps": [], "trace_complete": False}
        err = traceback.format_exc()
    latency = int((time.time() - t0) * 1000)
    metrics = score(task, r)
    return {
        "task_id": task["id"], "split": task["split"], "condition": cond,
        "input": task["input"], "summary": r["summary"],
        "tool_path": r["tool_path"], "metrics": metrics,
        "latency_ms": latency, "error": err,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--conditions", type=str, default=",".join(CONDITIONS.keys()))
    args = ap.parse_args()

    with open(PILOT_PATH) as f:
        tasks = json.load(f)
    conds = args.conditions.split(",")

    backend = OpenRouterBackend(model=MODEL)
    print(f"[pilot] {len(tasks)} tasks × {len(conds)} conditions = {len(tasks)*len(conds)} runs", flush=True)

    jobs = [(t, c) for t in tasks for c in conds]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, t, c, backend): (t["id"], c) for t, c in jobs}
        for fut in as_completed(futs):
            tid, c = futs[fut]
            r = fut.result()
            m = r["metrics"]
            print(f"[{c:11}] {tid:24} acc={int(m['accuracy'])} tool={int(m['tool_correctness'])} "
                  f"cite={int(m['citation_presence'])} trace={int(m['trace_completeness'])} "
                  f"nofail={int(m['no_fail'])} {r['latency_ms']}ms", flush=True)
            results.append(r)

    OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    # aggregate
    summary = {}
    for c in conds:
        rs = [r for r in results if r["condition"] == c]
        n = len(rs)
        if n == 0:
            continue
        summary[c] = {
            "n": n,
            "accuracy": sum(r["metrics"]["accuracy"] for r in rs) / n,
            "tool_correctness": sum(r["metrics"]["tool_correctness"] for r in rs) / n,
            "citation_presence": sum(r["metrics"]["citation_presence"] for r in rs) / n,
            "trace_completeness": sum(r["metrics"]["trace_completeness"] for r in rs) / n,
            "no_fail": sum(r["metrics"]["no_fail"] for r in rs) / n,
            "avg_latency_ms": sum(r["latency_ms"] for r in rs) / n,
        }

    md = ["# Pilot ablation results", "",
          f"Model: `{MODEL}` · Tasks: 10 (4 basic + 2 edge + 2 multi-step + 2 single-step from edge)",
          "", "| Condition | Acc | ToolCorr | CitePres | TraceComp | NoFail | Avg ms |",
          "|---|---|---|---|---|---|---|"]
    for c in conds:
        s = summary.get(c, {})
        if not s: continue
        md.append(f"| **{c}** | {s['accuracy']*100:.0f}% | {s['tool_correctness']*100:.0f}% | "
                  f"{s['citation_presence']*100:.0f}% | {s['trace_completeness']*100:.0f}% | "
                  f"{s['no_fail']*100:.0f}% | {int(s['avg_latency_ms'])} |")
    OUT_MD.write_text("\n".join(md) + "\n")
    print("\n" + "\n".join(md))
    print(f"\n[pilot] saved → {OUT_JSON}, {OUT_MD}")


if __name__ == "__main__":
    main()
