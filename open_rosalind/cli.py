from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from .backends import build_backend
from .config import load_config
from .harness import AgentAdapter, Task, TaskRunner, TaskTraceStore
from .orchestrator import Agent
from .skills import SKILLS, list_cards, get_skill


def cmd_serve(args):
    cfg = load_config(args.config)
    server_cfg = cfg.get("server", {})
    uvicorn.run(
        "open_rosalind.server:app",
        host=args.host or server_cfg.get("host", "0.0.0.0"),
        port=args.port or server_cfg.get("port", 6006),
        reload=False,
    )


def cmd_ask(args):
    cfg = load_config(args.config)
    agent = Agent(build_backend(cfg["backend"]), trace_dir=cfg.get("trace", {}).get("dir", "./traces"))
    question = args.question if args.question else sys.stdin.read()
    result = agent.analyze(question)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"# session: {result['session_id']}  skill: {result['skill']}\n")
        print(result["summary"])
        print(f"\n(trace → {result['trace_path']})")


def cmd_skills_list(args):
    if args.json:
        print(json.dumps(list_cards(), indent=2, ensure_ascii=False))
        return
    cards = list_cards()
    print(f"{len(cards)} skill(s) registered:\n")
    name_w = max(len(c["name"]) for c in cards)
    cat_w = max(len(c["category"]) for c in cards)
    for c in cards:
        tools = ",".join(c["tools_used"]) or "—"
        print(f"  {c['name']:<{name_w}}  [{c['category']:<{cat_w}}]  "
              f"safety={c['safety_level']:<7}  tools={tools}")
        print(f"     {c['description']}")


def cmd_skills_inspect(args):
    sk = get_skill(args.name)
    if sk is None:
        print(f"unknown skill: {args.name}", file=sys.stderr)
        print("known: " + ", ".join(SKILLS), file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(sk.to_full(), indent=2, ensure_ascii=False))
        return
    full = sk.to_full()
    print(f"# {full['name']}  ({full['category']}, safety={full['safety_level']})\n")
    print(full["description"] + "\n")
    print(f"tools_used: {', '.join(full['tools_used']) or '—'}\n")
    print("input_schema:")
    print(json.dumps(full["input_schema"], indent=2))
    print("\noutput_schema:")
    print(json.dumps(full["output_schema"], indent=2))
    if full["examples"]:
        print("\nexamples:")
        for i, ex in enumerate(full["examples"], 1):
            print(f"  [{i}] input  = {json.dumps(ex.get('input'), ensure_ascii=False)}")
            print(f"      expects = {ex.get('expects')}")


def cmd_task_run(args):
    """Run a multi-step task."""
    cfg = load_config(args.config)
    agent = Agent(build_backend(cfg["backend"]), trace_dir=cfg.get("trace", {}).get("dir", "./traces"))
    adapter = AgentAdapter(agent)
    runner = TaskRunner(adapter)
    trace_store = TaskTraceStore()

    # Generate task_id
    from datetime import datetime
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    task = Task(task_id=task_id, user_goal=args.goal, max_steps=args.max_steps)
    result = runner.run(task)
    trace_store.save(result)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"✅ Task {result.task_id} completed")
        print(f"   Status: {result.status}")
        print(f"   Steps: {len(result.steps)}")
        print(f"   Evidence: {len(result.state.evidence_pool)} records")
        print(f"   Trace: task_traces/{result.task_id}.jsonl")
        if result.warnings:
            print(f"   Warnings: {len(result.warnings)}")


def cmd_task_status(args):
    """Show task status."""
    trace_store = TaskTraceStore()
    events = trace_store.load(args.task_id)
    if not events:
        print(f"❌ Task {args.task_id} not found")
        return

    if args.json:
        print(json.dumps(events, indent=2, ensure_ascii=False))
    else:
        task_start = next((e for e in events if e["kind"] == "task_start"), None)
        task_complete = next((e for e in events if e["kind"] == "task_complete"), None)
        steps = [e for e in events if e["kind"] == "step"]

        if task_start:
            print(f"Task: {task_start['task_id']}")
            print(f"Goal: {task_start['user_goal']}")
            print(f"Max steps: {task_start['max_steps']}")
        print(f"\nSteps: {len(steps)}")
        for s in steps:
            status_icon = "✅" if s["status"] == "success" else "❌"
            print(f"  {status_icon} {s['step_id']}: {s['instruction'][:60]}...")
        if task_complete:
            print(f"\nStatus: {task_complete['status']}")
            if task_complete.get("warnings"):
                print(f"Warnings: {len(task_complete['warnings'])}")


def cmd_task_trace(args):
    """Show task trace."""
    trace_store = TaskTraceStore()
    events = trace_store.load(args.task_id)
    if not events:
        print(f"❌ Task {args.task_id} not found")
        return
    print(json.dumps(events, indent=2, ensure_ascii=False))


def cmd_task_report(args):
    """Show final report."""
    trace_store = TaskTraceStore()
    events = trace_store.load(args.task_id)
    if not events:
        print(f"❌ Task {args.task_id} not found")
        return
    task_complete = next((e for e in events if e["kind"] == "task_complete"), None)
    if task_complete and task_complete.get("final_report"):
        print(task_complete["final_report"])
    else:
        print("❌ No final report available")


def main():
    p = argparse.ArgumentParser(prog="open-rosalind")
    p.add_argument("--config", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("serve", help="Run the web API + UI")
    ps.add_argument("--host", default=None)
    ps.add_argument("--port", type=int, default=None)
    ps.set_defaults(func=cmd_serve)

    pa = sub.add_parser("ask", help="One-shot CLI question")
    pa.add_argument("question", nargs="?", default=None)
    pa.add_argument("--json", action="store_true")
    pa.set_defaults(func=cmd_ask)

    # alias `run` → `ask` (mvp2.md naming)
    pr = sub.add_parser("run", help="Alias for `ask`")
    pr.add_argument("question", nargs="?", default=None)
    pr.add_argument("--json", action="store_true")
    pr.set_defaults(func=cmd_ask)

    psk = sub.add_parser("skills", help="Inspect the Bio Skills Registry")
    psk_sub = psk.add_subparsers(dest="skills_cmd", required=True)

    pl = psk_sub.add_parser("list", help="List all registered skills")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_skills_list)

    pi = psk_sub.add_parser("inspect", help="Show full metadata for one skill")
    pi.add_argument("name")
    pi.add_argument("--json", action="store_true")
    pi.set_defaults(func=cmd_skills_inspect)

    # task subcommands (MVP3)
    pt = sub.add_parser("task", help="Multi-step task execution (MVP3)")
    pt_sub = pt.add_subparsers(dest="task_cmd", required=True)

    ptr = pt_sub.add_parser("run", help="Run a multi-step task")
    ptr.add_argument("goal", help="Natural-language task goal")
    ptr.add_argument("--max-steps", type=int, default=5)
    ptr.add_argument("--json", action="store_true")
    ptr.set_defaults(func=cmd_task_run)

    pts = pt_sub.add_parser("status", help="Show task status")
    pts.add_argument("task_id")
    pts.add_argument("--json", action="store_true")
    pts.set_defaults(func=cmd_task_status)

    ptt = pt_sub.add_parser("trace", help="Show task trace")
    ptt.add_argument("task_id")
    ptt.set_defaults(func=cmd_task_trace)

    ptrep = pt_sub.add_parser("report", help="Show final report")
    ptrep.add_argument("task_id")
    ptrep.set_defaults(func=cmd_task_report)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
