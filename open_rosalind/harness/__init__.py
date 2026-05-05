"""Harness module: Multi-step task execution for Open-Rosalind MVP3.

Harness manages tasks and executes scientific work only through AgentAdapter.
"""
from .adapter import AgentAdapter
from .contracts import StepExecutor, StepResult
from .planner import ConstrainedPlanner
from .runner import TaskRunner
from .task import Task, TaskState, TaskStep
from .trace import TaskTraceStore

__all__ = [
    "Task",
    "TaskStep",
    "TaskState",
    "AgentAdapter",
    "StepExecutor",
    "StepResult",
    "ConstrainedPlanner",
    "TaskRunner",
    "TaskTraceStore",
]
