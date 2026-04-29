from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from .backends import build_backend
from .config import load_config
from .harness import AgentAdapter, Task, TaskRunner, TaskTraceStore
from .orchestrator import Agent
from .orchestrator.mode_selector import select_mode
from .orchestrator.runner import AgentRunner
from .skills import SKILLS, list_cards, get_skill
from .skills_v2 import SKILLS_V2  # MVP3.1 modular skills
from .storage import Storage  # MVP3.2 SQLite storage

cfg = load_config()
backend = build_backend(cfg["backend"])
agent = Agent(backend, trace_dir=cfg.get("trace", {}).get("dir", "./traces"))
runner = AgentRunner(agent)

# MVP3 harness
harness_adapter = AgentAdapter(agent)
harness_runner = TaskRunner(harness_adapter)
task_trace_store = TaskTraceStore()

# MVP3.2 storage
storage = Storage(db_path=cfg.get("storage", {}).get("db_path", "./open_rosalind.db"))

app = FastAPI(title="Open-Rosalind", version="0.3.2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== MVP3.2 Auth helpers =====

def get_user_from_header(authorization: str | None = None) -> dict:
    """Extract user from Authorization header. Returns anonymous user if no token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        user = storage.user_from_token(token)
        if user:
            return user
    # Fall back to anonymous user (creates a fresh one each time without token)
    return storage.create_anonymous_user()


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


@app.get("/api/skillsv2")
def list_skills_v2():
    """List all auto-discovered skills from skills_v2/."""
    return {
        "skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "category": skill.category,
                "safety_level": skill.safety_level,
                "tools_used": skill.tools_used,
            }
            for skill in SKILLS_V2.values()
        ],
        "count": len(SKILLS_V2),
    }


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


_WEB_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
if _WEB_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(_WEB_DIR / "assets")), name="assets")

    @app.get("/")
    def index():
        return FileResponse(str(_WEB_DIR / "index.html"))


# ===== MVP3 Task API =====

class TaskRunRequest(BaseModel):
    goal: str = Field(..., max_length=5000)
    max_steps: int = Field(5, ge=1, le=10)


class TaskRunResponse(BaseModel):
    task_id: str
    status: str
    steps: list[dict]
    final_report: str | None
    warnings: list[str]


@app.post("/api/task/run", response_model=TaskRunResponse)
def task_run(req: TaskRunRequest):
    """Run a multi-step task."""
    from datetime import datetime
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
    
    task = Task(task_id=task_id, user_goal=req.goal, max_steps=req.max_steps)
    result = harness_runner.run(task)
    task_trace_store.save(result)
    
    return TaskRunResponse(
        task_id=result.task_id,
        status=result.status,
        steps=[
            {
                "step_id": s.step_id,
                "instruction": s.instruction,
                "status": s.status,
                "latency_ms": s.latency_ms,
                "summary": s.agent_result.get("summary", "") if s.agent_result else "",
            }
            for s in result.steps
        ],
        final_report=result.final_report,
        warnings=result.warnings,
    )


@app.get("/api/task/{task_id}")
def task_status(task_id: str):
    """Get task status and trace."""
    events = task_trace_store.load(task_id)
    if not events:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "events": events}


# ===== MVP3.2 Auth API =====

class SignupRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    token: str


@app.post("/api/auth/signup", response_model=AuthResponse)
def signup(req: SignupRequest):
    """Sign up with email + password (no email verification)."""
    if storage.get_user_by_email(req.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = storage.create_user(req.email, req.password)
    token = storage.create_token(user["user_id"])
    return AuthResponse(user_id=user["user_id"], email=user["email"], token=token)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest):
    """Log in with email + password."""
    user = storage.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = storage.create_token(user["user_id"])
    return AuthResponse(user_id=user["user_id"], email=user["email"], token=token)


@app.get("/api/auth/me")
def me(authorization: str | None = Header(None)):
    """Get current user. Requires Authorization: Bearer <token>."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization[7:]
    user = storage.user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "is_anonymous": bool(user["is_anonymous"]),
    }


# ===== MVP3.2 Chat API (auto mode + storage) =====

class ChatRequest(BaseModel):
    message: str = Field(..., max_length=20000)
    session_id: str | None = None  # continue an existing chat session
    anon_token: str | None = None  # for anonymous users to reuse their slot


class ChatResponse(BaseModel):
    session_id: str
    user_id: str
    execution_mode: str
    execution_reason: str
    skill: str | None = None
    summary: str
    annotation: dict | None = None
    confidence: float | None = None
    notes: list[str] = []
    evidence: dict | None = None
    trace_steps: list[dict] = []
    final_report: str | None = None
    steps: list[dict] = []
    anon_token: str | None = None  # returned to anonymous users for reuse
    requires_signup: bool = False  # true when anon user tries to start a new session
    is_anonymous: bool = False


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, authorization: str | None = Header(None)):
    """
    Unified chat endpoint with auto mode selection.

    Anonymous policy:
    - Anonymous users get exactly ONE session (their first conversation)
    - Continuing the existing session is allowed (same anon_token + same session_id)
    - Trying to start a new session as anonymous → returns requires_signup=True
    - To save more sessions, the user must sign up

    Authenticated users have unlimited sessions.
    """
    # 1. Resolve user (auth or anonymous)
    is_anonymous = False
    new_anon_token = None

    if authorization and authorization.startswith("Bearer "):
        user = storage.user_from_token(authorization[7:])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
    elif req.anon_token:
        # Existing anonymous user — verify their token
        user = storage.user_from_token(req.anon_token)
        if not user or not user.get("is_anonymous"):
            # Invalid anon token — create fresh anonymous user
            user = storage.create_anonymous_user()
            new_anon_token = storage.create_token(user["user_id"])
        else:
            is_anonymous = True
    else:
        # First-time anonymous visitor
        user = storage.create_anonymous_user()
        new_anon_token = storage.create_token(user["user_id"])
        is_anonymous = True

    # 2. Anonymous session limit: only allow ONE session
    if user.get("is_anonymous"):
        is_anonymous = True
        existing_sessions = storage.list_sessions(user["user_id"], limit=2)
        # If trying to start a NEW session (no session_id) and they already have one
        # OR session_id provided but doesn't match their existing one
        existing_ids = [s["session_id"] for s in existing_sessions]
        if existing_sessions:
            if req.session_id is None or req.session_id not in existing_ids:
                # New session attempt — block and prompt signup
                return ChatResponse(
                    session_id="",
                    user_id=user["user_id"],
                    execution_mode="blocked",
                    execution_reason="anonymous users limited to one session — please sign up to start new conversations",
                    skill=None,
                    summary="🔒 **Sign up required**\n\nAnonymous users can have one conversation. To start a new session, please [sign up](#signup) (email + password, no verification needed).",
                    annotation={"kind": "auth_required"},
                    confidence=None,
                    notes=["Anonymous session limit reached"],
                    requires_signup=True,
                    is_anonymous=True,
                    anon_token=new_anon_token or req.anon_token,
                )

    # 3. Auto-select mode
    mode, reason = select_mode(req.message)

    # Determine the chat session_id (sticky across turns within a conversation)
    chat_session_id = req.session_id

    # 3. Run skill
    if mode == "harness":
        from datetime import datetime
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:20]}"
        task = Task(task_id=task_id, user_goal=req.message, max_steps=5)
        result = harness_runner.run(task)
        task_trace_store.save(result)

        # If this is the first turn of a new conversation, use task_id as chat session
        if not chat_session_id:
            chat_session_id = task_id

        # Save session metadata (used for sidebar listing)
        storage.save_session(
            session_id=chat_session_id,
            user_id=user["user_id"],
            user_input=req.message,
            skill="harness",
            summary=result.final_report or "",
            confidence=0.85,
            annotation={"kind": "task", "n_steps": len(result.steps)},
            evidence={"steps": [{"step_id": s.step_id, "status": s.status} for s in result.steps]},
            notes=result.warnings,
            execution_mode=mode,
            execution_reason=reason,
        )

        # Build the assistant card (matches ChatResponse shape minus session_id)
        assistant_card = {
            "execution_mode": mode,
            "execution_reason": reason,
            "skill": "harness",
            "summary": result.final_report or "",
            "annotation": {"kind": "task", "n_steps": len(result.steps)},
            "confidence": 0.85,
            "notes": result.warnings,
            "final_report": result.final_report,
            "steps": [
                {
                    "step_id": s.step_id,
                    "instruction": s.instruction,
                    "status": s.status,
                    "summary": s.agent_result.get("summary", "") if s.agent_result else "",
                }
                for s in result.steps
            ],
        }
        # Persist message turns (user + assistant) for full conversation replay
        storage.add_message(chat_session_id, "user", req.message)
        storage.add_message(chat_session_id, "assistant", result.final_report or "", card=assistant_card)

        return ChatResponse(
            session_id=chat_session_id,
            user_id=user["user_id"],
            **assistant_card,
            anon_token=new_anon_token or req.anon_token if is_anonymous else None,
            is_anonymous=is_anonymous,
        )
    else:
        # Single-step mode (use existing AgentRunner)
        # When session_id is provided (continuing a conversation), use it as
        # follow_up_session so the runner loads prior evidence from JSONL.
        # The chat_session_id matches the JSONL session because the agent reuses it.
        result = runner.run(
            req.message,
            follow_up_session=req.session_id,
        )

        # Use the agent's session_id as the chat session if this is a new conversation
        if not chat_session_id:
            chat_session_id = result["session_id"]

        storage.save_session(
            session_id=chat_session_id,
            user_id=user["user_id"],
            user_input=req.message,
            skill=result.get("skill", ""),
            summary=result.get("summary", ""),
            confidence=result.get("confidence") or 0.0,
            annotation=result.get("annotation") or {},
            evidence=result.get("evidence") or {},
            notes=result.get("notes") or [],
            execution_mode=mode,
            execution_reason=reason,
        )

        # Build the assistant card and persist messages
        assistant_card = {
            "execution_mode": mode,
            "execution_reason": reason,
            "skill": result.get("skill"),
            "summary": result.get("summary", ""),
            "annotation": result.get("annotation"),
            "confidence": result.get("confidence"),
            "notes": result.get("notes") or [],
            "evidence": result.get("evidence"),
            "trace_steps": result.get("trace_steps") or [],
        }
        storage.add_message(chat_session_id, "user", req.message)
        storage.add_message(chat_session_id, "assistant", result.get("summary", ""), card=assistant_card)

        return ChatResponse(
            session_id=chat_session_id,
            user_id=user["user_id"],
            **assistant_card,
            anon_token=new_anon_token or req.anon_token if is_anonymous else None,
            is_anonymous=is_anonymous,
        )


@app.get("/api/chat/sessions")
def list_chat_sessions(authorization: str | None = Header(None), anon_token: str | None = None, limit: int = 50):
    """List user's chat sessions (works for both authenticated and anonymous)."""
    user = None
    if authorization and authorization.startswith("Bearer "):
        user = storage.user_from_token(authorization[7:])
    elif anon_token:
        user = storage.user_from_token(anon_token)
    if not user:
        return {"sessions": []}
    return {"sessions": storage.list_sessions(user["user_id"], limit=limit)}


@app.get("/api/chat/sessions/{session_id}")
def get_chat_session(session_id: str, authorization: str | None = Header(None), anon_token: str | None = None):
    """Get full session detail with all message turns."""
    # Resolve user from either Bearer token or anon_token query param
    user = None
    if authorization and authorization.startswith("Bearer "):
        user = storage.user_from_token(authorization[7:])
    elif anon_token:
        user = storage.user_from_token(anon_token)

    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    session = storage.get_session(session_id, user["user_id"])
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Include full message history for replay
    messages = storage.get_messages(session_id)
    session["messages"] = messages
    return session
