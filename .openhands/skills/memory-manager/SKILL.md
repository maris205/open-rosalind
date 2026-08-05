---
name: memory-manager
description: Use when creating, updating, summarizing, or auditing structured project memory for Open-Rosalind Agent.
---
# Memory Manager Skill

Use this skill when the Agent needs to maintain project memory across tasks.

## Purpose

Turn conversations, uploaded files, evidence, decisions, and tool outputs into structured memory records.

## Memory Types

- Project memory: topic, scope, hypotheses, terminology, user preferences
- Evidence memory: papers, sequence records, datasets, verified references, source locators
- Task memory: plans, tool calls, outputs, failures, follow-up actions
- Decision memory: accepted assumptions, rejected claims, selected methods

## Output Structure

1. Memory update summary
2. New facts to store
3. Evidence records to attach
4. Decisions to record
5. Open questions
6. Items not safe to store as facts

## Rules

- Do not store unverified model guesses as facts.
- Every stored evidence item should have a source locator when possible.
- Keep user-provided information separate from inferred information.
- Mark stale or conflicting memory.
