from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .backends import build_backend
from .config import load_config
from .orchestrator import Agent
from .orchestrator.runner import AgentRunner
from .skills import SKILLS, list_cards, get_skill

cfg = load_config()
backend = build_backend(cfg["backend"])
agent = Agent(backend, trace_dir=cfg.get("trace", {}).get("dir", "./traces"))
runner = AgentRunner(agent)

app = FastAPI(title="Open-Rosalind", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    question: str | None = Field(None, max_length=20000)
    input: str | None = Field(None, max_length=20000)
    mode: str | None = Field(None, description="auto | sequence | uniprot | literature | mutation")
    session_id: str | None = None
    follow_up_session: str | None = Field(None, description="Session ID to load prior evidence from for follow-up")

    def get_text(self) -> str:
        text = self.question or self.input or ""
        if not text.strip():
            raise ValueError("question/input is required")
        return text


class AnalyzeResponse(BaseModel):
    session_id: str
    skill: str
    summary: str
    annotation: dict | None = None
    confidence: float | None = None
    notes: list[str] = []
    evidence: dict
    trace_path: str
    trace: list[dict]
    trace_steps: list[dict]


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "backend": backend.name,
        "model": cfg["backend"].get("model"),
        "n_skills": len(SKILLS),
    }


@app.get("/api/skills")
def skills_list():
    return {"skills": list_cards()}


@app.get("/api/skills/{name}")
def skill_detail(name: str):
    sk = get_skill(name)
    if sk is None:
        raise HTTPException(status_code=404, detail=f"skill not found: {name}")
    return sk.to_full()


@app.get("/api/sessions")
def sessions_list(limit: int = 50):
    return {"sessions": agent.session_store.list_sessions(limit=limit)}


@app.get("/api/sessions/{session_id}")
def session_detail(session_id: str):
    events = agent.session_store.read_session(session_id)
    if not events:
        raise HTTPException(status_code=404, detail=f"session not found: {session_id}")
    return {"session_id": session_id, "events": [e.to_dict() for e in events]}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    try:
        text = req.get_text()
        result = runner.run(
            text,
            session_id=req.session_id,
            mode=req.mode,
            follow_up_session=req.follow_up_session,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}") from e
    return AnalyzeResponse(**result)


_WEB_DIR = Path(__file__).resolve().parent.parent / "web"
if _WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(_WEB_DIR / "index.html"))
