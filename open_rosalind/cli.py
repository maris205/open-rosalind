from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from .backends import build_backend
from .config import load_config
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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
