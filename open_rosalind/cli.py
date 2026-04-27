from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from .backends import build_backend
from .config import load_config
from .orchestrator import Agent


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

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
