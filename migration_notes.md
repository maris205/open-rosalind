# Migration Notes

## Current architecture

- Backend entrypoint: `open_rosalind/server.py`
  - Runs the FastAPI app.
  - Serves the built frontend from `web/dist` when present.
  - Exposes both the current chat API (`/api/chat`) and older compatibility APIs (`/api/analyze`, `/api/sessions`).
- Model/backend layer: `open_rosalind/backends/`
  - `factory.py` builds an OpenAI-compatible backend.
  - Default config in `configs/default.yaml` uses OpenRouter with model `google/gemma-4-26b-a4b-it`.
- Single-step execution path:
  - `orchestrator/mode_selector.py` decides `single_step` vs `harness`.
  - `orchestrator/runner.py` wraps follow-up handling.
  - `orchestrator/agent.py` routes the request, calls one registered skill, logs trace/session events, then asks the model to summarize from evidence only.
  - `orchestrator/router.py` is rule-based with optional LLM intent classification from `orchestrator/intent_classifier.py`.
- Multi-step execution path:
  - `harness/planner.py` selects a fixed template plan.
  - `harness/runner.py` executes steps sequentially.
  - `harness/adapter.py` is the boundary between Harness and Agent.
  - Harness does not call tools directly; it delegates step execution through `AgentAdapter`.
- Skill/tool layer:
  - Active runtime registry: `open_rosalind/skills/`
  - Active atomic tools: `open_rosalind/tools/`
  - Transitional modular registry: `open_rosalind/skills_v2/`
    - Auto-discovered and exposed by `/api/skillsv2`
    - Not the main runtime dispatch path yet
- Persistence:
  - SQLite app storage: `open_rosalind/storage.py`
  - JSONL session logs: `sessions/`
  - JSONL trace logs: `traces/`
  - JSONL task traces: `task_traces/`
- Frontend:
  - Current UI: `web-react/`
  - Landing page and chat app live under `web-react/src/`
  - Vite build output goes to `web/dist/`
  - Legacy static UI remains in `web/`

## Dev server

### Backend API

Current Python package metadata in `pyproject.toml` does not include every imported runtime dependency. In practice, the backend currently needs:

```bash
pip install -e .
pip install pyyaml
```

If the model backend is OpenRouter, set:

```bash
export OPENROUTER_API_KEY=...
```

Run the backend:

```bash
python -m open_rosalind.cli serve --port 6006
```

The FastAPI server listens on `http://127.0.0.1:6006` by default.

### React frontend

Install frontend dependencies once:

```bash
cd web-react
npm install
```

Run the frontend dev server:

```bash
npm run dev
```

Vite serves the UI on `http://127.0.0.1:3000` and proxies `/api` requests to `http://127.0.0.1:6006`.

### Built frontend

To rebuild the production UI bundle that FastAPI serves from `web/dist`:

```bash
cd web-react
npm run build
```

## Test commands

Required project validation commands from `AGENTS.md`:

```bash
pytest
python benchmark/run_biobench.py
```

Additional benchmark/helper commands present in the repository:

```bash
python benchmark/run_biobench_v03.py
python benchmark/run_pilot.py
python benchmark/run_scaled.py
python benchmark/run_paired.py
```
