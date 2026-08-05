"""Database and authentication primitives for Open-Rosalind Agent."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, create_engine, delete, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = ROOT / "data" / "rosalind.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")
SESSION_DAYS = int(os.environ.get("ROSALIND_SESSION_DAYS", "14"))
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    sessions: Mapped[list["LoginSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class LoginSession(Base):
    __tablename__ = "login_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="sessions")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    permission_level: Mapped[int] = mapped_column(Integer, default=3)
    code_sha256: Mapped[str] = mapped_column(String(64))
    image: Mapped[str] = mapped_column(String(255))
    config_json: Mapped[str] = mapped_column(Text)
    started_at: Mapped[float] = mapped_column(Float)
    ended_at: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    audit_json: Mapped[str] = mapped_column(Text, default="{}")


class JobFile(Base):
    __tablename__ = "job_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(1024))
    size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(2048))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(32))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class MessageFeedback(Base):
    __tablename__ = "message_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    message_id: Mapped[str] = mapped_column(String(100), index=True)
    chat_id: Mapped[str] = mapped_column(String(100), index=True)
    skill: Mapped[str] = mapped_column(String(100), index=True)
    rating: Mapped[str] = mapped_column(String(12), index=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ProjectMemory(Base):
    __tablename__ = "project_memory"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(40), default="user")
    source_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class TaskPlan(Base):
    __tablename__ = "task_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("task_plans.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240))
    instruction: Mapped[str] = mapped_column(Text)
    skill: Mapped[str] = mapped_column(String(100), default="agent-planner")
    status: Mapped[str] = mapped_column(String(32), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


if DATABASE_URL.startswith("sqlite:///"):
    Path(DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False, "timeout": 5} if DATABASE_URL.startswith("sqlite") else {},
)


if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


SessionLocal = sessionmaker(engine, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def initialize_database() -> None:
    Base.metadata.create_all(engine)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_credentials(email: str, password: str) -> tuple[str, str]:
    normalized = normalize_email(email)
    if len(normalized) > 320 or not EMAIL_RE.fullmatch(normalized):
        raise ValueError("请输入有效的邮箱地址。")
    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符。")
    if len(password) > 128:
        raise ValueError("密码不能超过 128 个字符。")
    return normalized, password


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = encoded.split("$", 5)
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected_hex)),
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str) -> dict[str, str]:
    normalized, password = validate_credentials(email, password)
    with SessionLocal.begin() as db:
        if db.scalar(select(User).where(User.email == normalized)):
            raise ValueError("该邮箱已经注册。")
        user = User(id=str(uuid.uuid4()), email=normalized, password_hash=hash_password(password), created_at=utcnow())
        db.add(user)
    return {"id": user.id, "email": user.email}


def authenticate_user(email: str, password: str) -> dict[str, str] | None:
    normalized = normalize_email(email)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == normalized))
        if not user or not verify_password(password, user.password_hash):
            return None
        return {"id": user.id, "email": user.email}


def create_login_session(user_id: str) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    expires_at = now + timedelta(days=SESSION_DAYS)
    with SessionLocal.begin() as db:
        db.add(
            LoginSession(
                token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
                user_id=user_id,
                created_at=now,
                expires_at=expires_at,
                last_seen_at=now,
            )
        )
    return token, expires_at


def get_user_for_token(token: str) -> dict[str, str] | None:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = utcnow()
    with SessionLocal.begin() as db:
        login = db.get(LoginSession, token_hash)
        if not login:
            return None
        expires_at = login.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            db.delete(login)
            return None
        login.last_seen_at = now
        user = db.get(User, login.user_id)
        return {"id": user.id, "email": user.email} if user else None


def delete_login_session(token: str) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with SessionLocal.begin() as db:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == token_hash))


def record_message_feedback(
    user_id: str,
    message_id: str,
    chat_id: str,
    skill: str,
    rating: str,
    content: str,
) -> dict[str, object]:
    message_id = message_id.strip()[:100]
    chat_id = chat_id.strip()[:100]
    skill = skill.strip()[:100]
    rating = rating.strip().lower()
    if not message_id or not chat_id:
        raise ValueError("缺少消息或对话标识。")
    if rating not in {"like", "dislike", "none"}:
        raise ValueError("不支持的反馈类型。")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    now = utcnow()
    with SessionLocal.begin() as db:
        feedback = db.scalar(
            select(MessageFeedback).where(
                MessageFeedback.user_id == user_id,
                MessageFeedback.message_id == message_id,
            )
        )
        if rating == "none":
            if feedback:
                db.delete(feedback)
            return {"messageId": message_id, "rating": "none", "updatedAt": now.isoformat()}
        if feedback:
            feedback.chat_id = chat_id
            feedback.skill = skill
            feedback.rating = rating
            feedback.content_sha256 = digest
            feedback.updated_at = now
        else:
            feedback = MessageFeedback(
                id=str(uuid.uuid4()),
                user_id=user_id,
                message_id=message_id,
                chat_id=chat_id,
                skill=skill,
                rating=rating,
                content_sha256=digest,
                created_at=now,
                updated_at=now,
            )
            db.add(feedback)
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_id=None,
                action="message.feedback",
                status=rating,
                payload_json=json.dumps(
                    {
                        "messageId": message_id,
                        "chatId": chat_id,
                        "skill": skill,
                        "contentSha256": digest,
                    },
                    ensure_ascii=False,
                ),
                created_at=now,
            )
        )
    return {"messageId": message_id, "rating": rating, "updatedAt": now.isoformat()}


def create_job(job_id: str, user_id: str, code_sha256: str, image: str, config: dict, started_at: float) -> None:
    with SessionLocal.begin() as db:
        db.add(
            Job(
                id=job_id,
                user_id=user_id,
                status="running",
                permission_level=3,
                code_sha256=code_sha256,
                image=image,
                config_json=json.dumps(config, ensure_ascii=False),
                started_at=started_at,
            )
        )


def finish_job(job_id: str, audit: dict, stdout: str, stderr: str, files: list[dict]) -> None:
    with SessionLocal.begin() as db:
        job = db.get(Job, job_id)
        if not job:
            return
        job.status = str(audit["status"])
        job.ended_at = float(audit["endedAt"])
        job.duration_seconds = float(audit["durationSeconds"])
        job.exit_code = audit.get("exitCode")
        job.stdout = stdout
        job.stderr = stderr
        job.audit_json = json.dumps(audit, ensure_ascii=False)
        for item in files:
            db.add(
                JobFile(
                    job_id=job_id,
                    name=str(item["name"]),
                    size=int(item["size"]),
                    sha256=str(item["sha256"]),
                    path=str(item["name"]),
                )
            )
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                user_id=job.user_id,
                job_id=job_id,
                action="python.execute",
                status=job.status,
                payload_json=json.dumps(audit, ensure_ascii=False),
                created_at=utcnow(),
            )
        )


def user_owns_job(user_id: str, job_id: str) -> bool:
    with SessionLocal() as db:
        return db.scalar(select(Job.id).where(Job.id == job_id, Job.user_id == user_id)) is not None


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def create_project(owner_id: str, name: str, description: str = "") -> dict[str, object]:
    name = name.strip()
    description = description.strip()
    if not name or len(name) > 200:
        raise ValueError("项目名称需要为 1-200 个字符。")
    now = utcnow()
    project = Project(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        name=name,
        description=description[:4000],
        created_at=now,
        updated_at=now,
    )
    with SessionLocal.begin() as db:
        db.add(project)
    return serialize_project(project)


def serialize_project(project: Project) -> dict[str, object]:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "createdAt": serialize_datetime(project.created_at),
        "updatedAt": serialize_datetime(project.updated_at),
    }


def list_projects(owner_id: str) -> list[dict[str, object]]:
    with SessionLocal() as db:
        projects = db.scalars(
            select(Project).where(Project.owner_id == owner_id).order_by(Project.updated_at.desc())
        ).all()
        return [serialize_project(project) for project in projects]


def user_owns_project(user_id: str, project_id: str) -> bool:
    with SessionLocal() as db:
        return db.scalar(select(Project.id).where(Project.id == project_id, Project.owner_id == user_id)) is not None


def add_project_memory(
    project_id: str,
    user_id: str,
    category: str,
    content: str,
    source_type: str = "user",
    source_id: str = "",
) -> dict[str, object]:
    allowed = {"fact", "evidence", "decision", "constraint", "open_question", "conclusion"}
    if category not in allowed:
        raise ValueError("不支持的记忆类型。")
    content = content.strip()
    if not content or len(content) > 20_000:
        raise ValueError("记忆内容需要为 1-20000 个字符。")
    if not user_owns_project(user_id, project_id):
        raise PermissionError("项目不存在。")
    memory = ProjectMemory(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=user_id,
        category=category,
        content=content,
        source_type=source_type[:40],
        source_id=source_id[:64],
        created_at=utcnow(),
    )
    with SessionLocal.begin() as db:
        db.add(memory)
        project = db.get(Project, project_id)
        if project:
            project.updated_at = utcnow()
    return serialize_memory(memory)


def serialize_memory(memory: ProjectMemory) -> dict[str, object]:
    return {
        "id": memory.id,
        "category": memory.category,
        "content": memory.content,
        "sourceType": memory.source_type,
        "sourceId": memory.source_id,
        "createdAt": serialize_datetime(memory.created_at),
    }


def create_task_plan(project_id: str, user_id: str, goal: str, steps: list[dict[str, str]]) -> dict[str, object]:
    goal = goal.strip()
    if not user_owns_project(user_id, project_id):
        raise PermissionError("项目不存在。")
    if not goal or len(goal) > 20_000:
        raise ValueError("任务目标需要为 1-20000 个字符。")
    if not 1 <= len(steps) <= 10:
        raise ValueError("任务计划必须包含 1-10 个步骤。")
    now = utcnow()
    plan = TaskPlan(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=user_id,
        goal=goal,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    with SessionLocal.begin() as db:
        db.add(plan)
        for position, item in enumerate(steps, start=1):
            title = str(item.get("title", "")).strip()[:240] or f"步骤 {position}"
            instruction = str(item.get("instruction", "")).strip()[:20_000]
            if not instruction:
                raise ValueError(f"步骤 {position} 缺少执行说明。")
            db.add(
                TaskStep(
                    id=str(uuid.uuid4()),
                    plan_id=plan.id,
                    position=position,
                    title=title,
                    instruction=instruction,
                    skill=str(item.get("skill", "agent-planner"))[:100],
                    status="pending",
                    attempts=0,
                )
            )
        project = db.get(Project, project_id)
        if project:
            project.updated_at = now
    return get_task_plan(user_id, plan.id) or {}


def serialize_step(step: TaskStep) -> dict[str, object]:
    return {
        "id": step.id,
        "position": step.position,
        "title": step.title,
        "instruction": step.instruction,
        "skill": step.skill,
        "status": step.status,
        "attempts": step.attempts,
        "output": step.output,
        "error": step.error,
        "startedAt": serialize_datetime(step.started_at),
        "completedAt": serialize_datetime(step.completed_at),
    }


def get_task_plan(user_id: str, plan_id: str) -> dict[str, object] | None:
    with SessionLocal() as db:
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == plan_id, TaskPlan.user_id == user_id))
        if not plan:
            return None
        steps = db.scalars(select(TaskStep).where(TaskStep.plan_id == plan.id).order_by(TaskStep.position)).all()
        return {
            "id": plan.id,
            "projectId": plan.project_id,
            "goal": plan.goal,
            "status": plan.status,
            "createdAt": serialize_datetime(plan.created_at),
            "updatedAt": serialize_datetime(plan.updated_at),
            "steps": [serialize_step(step) for step in steps],
        }


def get_project_workspace(user_id: str, project_id: str) -> dict[str, object] | None:
    with SessionLocal() as db:
        project = db.scalar(select(Project).where(Project.id == project_id, Project.owner_id == user_id))
        if not project:
            return None
        memories = db.scalars(
            select(ProjectMemory)
            .where(ProjectMemory.project_id == project_id)
            .order_by(ProjectMemory.created_at.desc())
            .limit(100)
        ).all()
        plans = db.scalars(
            select(TaskPlan)
            .where(TaskPlan.project_id == project_id, TaskPlan.user_id == user_id)
            .order_by(TaskPlan.created_at.desc())
            .limit(10)
        ).all()
        serialized_plans = []
        for plan in plans:
            steps = db.scalars(select(TaskStep).where(TaskStep.plan_id == plan.id).order_by(TaskStep.position)).all()
            serialized_plans.append(
                {
                    "id": plan.id,
                    "projectId": plan.project_id,
                    "goal": plan.goal,
                    "status": plan.status,
                    "createdAt": serialize_datetime(plan.created_at),
                    "updatedAt": serialize_datetime(plan.updated_at),
                    "steps": [serialize_step(step) for step in steps],
                }
            )
        return {
            "project": serialize_project(project),
            "memory": [serialize_memory(item) for item in memories],
            "plans": serialized_plans,
        }


def approve_task_plan(user_id: str, plan_id: str) -> dict[str, object] | None:
    with SessionLocal.begin() as db:
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == plan_id, TaskPlan.user_id == user_id))
        if not plan:
            return None
        if plan.status != "draft":
            raise ValueError("只有草稿计划可以确认。")
        plan.status = "approved"
        plan.updated_at = utcnow()
    return get_task_plan(user_id, plan_id)


def claim_next_task_step(user_id: str, plan_id: str) -> tuple[dict[str, object], dict[str, object]] | None:
    with SessionLocal.begin() as db:
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == plan_id, TaskPlan.user_id == user_id))
        if not plan:
            return None
        if plan.status not in {"approved", "running"}:
            raise ValueError("计划尚未确认，或当前状态不能执行。")
        step = db.scalar(
            select(TaskStep)
            .where(TaskStep.plan_id == plan.id, TaskStep.status == "pending")
            .order_by(TaskStep.position)
        )
        if not step:
            if not db.scalar(select(TaskStep.id).where(TaskStep.plan_id == plan.id, TaskStep.status == "running")):
                plan.status = "completed"
                plan.updated_at = utcnow()
            return ({"id": plan.id, "goal": plan.goal, "projectId": plan.project_id}, {})
        step.status = "running"
        step.attempts += 1
        step.started_at = utcnow()
        step.error = ""
        plan.status = "running"
        plan.updated_at = utcnow()
        previous = db.scalars(
            select(TaskStep)
            .where(TaskStep.plan_id == plan.id, TaskStep.position < step.position, TaskStep.status == "completed")
            .order_by(TaskStep.position)
        ).all()
        plan_data = {
            "id": plan.id,
            "goal": plan.goal,
            "projectId": plan.project_id,
            "previous": [serialize_step(item) for item in previous],
        }
        step_data = serialize_step(step)
    return plan_data, step_data


def finish_task_step(user_id: str, step_id: str, output: str = "", error: str = "") -> dict[str, object] | None:
    with SessionLocal.begin() as db:
        step = db.get(TaskStep, step_id)
        if not step:
            return None
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == step.plan_id, TaskPlan.user_id == user_id))
        if not plan:
            return None
        step.output = output[:100_000]
        step.error = error[:20_000]
        step.status = "completed" if not error else "failed"
        step.completed_at = utcnow()
        plan.status = "failed" if error else "running"
        if not error:
            remaining = db.scalar(select(TaskStep.id).where(TaskStep.plan_id == plan.id, TaskStep.status == "pending"))
            running = db.scalar(select(TaskStep.id).where(TaskStep.plan_id == plan.id, TaskStep.status == "running"))
            if not remaining and not running:
                plan.status = "completed"
        plan.updated_at = utcnow()
        db.add(
            AuditLog(
                id=str(uuid.uuid4()),
                user_id=user_id,
                job_id=None,
                action="task.step",
                status=step.status,
                payload_json=json.dumps(
                    {
                        "planId": plan.id,
                        "stepId": step.id,
                        "position": step.position,
                        "skill": step.skill,
                        "attempts": step.attempts,
                        "outputSha256": hashlib.sha256(step.output.encode("utf-8")).hexdigest() if step.output else "",
                        "error": step.error,
                    },
                    ensure_ascii=False,
                ),
                created_at=utcnow(),
            )
        )
    return get_task_plan(user_id, plan.id)


def retry_task_step(user_id: str, step_id: str) -> dict[str, object] | None:
    with SessionLocal.begin() as db:
        step = db.get(TaskStep, step_id)
        if not step:
            return None
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == step.plan_id, TaskPlan.user_id == user_id))
        if not plan:
            return None
        if step.status != "failed":
            raise ValueError("只有失败步骤可以重试。")
        step.status = "pending"
        step.error = ""
        step.output = ""
        step.started_at = None
        step.completed_at = None
        plan.status = "approved"
        plan.updated_at = utcnow()
    return get_task_plan(user_id, plan.id)


def project_memory_context(user_id: str, project_id: str, limit: int = 30) -> list[dict[str, object]]:
    with SessionLocal() as db:
        if not db.scalar(select(Project.id).where(Project.id == project_id, Project.owner_id == user_id)):
            return []
        rows = db.scalars(
            select(ProjectMemory)
            .where(ProjectMemory.project_id == project_id)
            .order_by(ProjectMemory.created_at.desc())
            .limit(limit)
        ).all()
        return [serialize_memory(row) for row in reversed(rows)]


def save_step_output_to_memory(user_id: str, step_id: str, category: str = "conclusion") -> dict[str, object]:
    with SessionLocal() as db:
        step = db.get(TaskStep, step_id)
        if not step or step.status != "completed" or not step.output.strip():
            raise ValueError("该步骤没有可保存的完成结果。")
        plan = db.scalar(select(TaskPlan).where(TaskPlan.id == step.plan_id, TaskPlan.user_id == user_id))
        if not plan:
            raise PermissionError("任务步骤不存在。")
        project_id = plan.project_id
        content = f"{step.title}\n\n{step.output}"
    return add_project_memory(
        project_id,
        user_id,
        category,
        content,
        source_type="task_step",
        source_id=step_id,
    )


def recover_interrupted_task_steps() -> list[str]:
    now = utcnow()
    recovered_plan_ids: set[str] = set()
    with SessionLocal.begin() as db:
        steps = db.scalars(select(TaskStep).where(TaskStep.status == "running")).all()
        for step in steps:
            step.status = "failed"
            step.error = "服务重启或执行中断，请确认上下文后重试此步骤。"
            step.completed_at = now
            plan = db.get(TaskPlan, step.plan_id)
            if plan:
                plan.status = "failed"
                plan.updated_at = now
                recovered_plan_ids.add(plan.id)
    return sorted(recovered_plan_ids)
