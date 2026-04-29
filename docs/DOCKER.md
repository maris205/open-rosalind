# Docker Deployment

Open-Rosalind ships with a multi-stage Dockerfile that builds the React UI and the Python backend into a single image.

---

## Quickstart with docker-compose

1. Set your OpenRouter key (or any OpenAI-compatible endpoint):

   ```bash
   export OPENROUTER_API_KEY=sk-or-v1-...
   ```

2. Build & run:

   ```bash
   docker compose up -d --build
   ```

3. Open http://localhost:8080/

To stop:

```bash
docker compose down
```

---

## Direct `docker run`

```bash
# Build
docker build -t open-rosalind:latest .

# Run
docker run -d \
  --name open-rosalind \
  -p 8080:80 \
  -e OPENROUTER_API_KEY=sk-or-v1-... \
  -e OPENROUTER_MODEL=google/gemma-4-26b-a4b-it \
  -v $(pwd)/sessions:/app/sessions \
  -v $(pwd)/traces:/app/traces \
  -v $(pwd)/open_rosalind.db:/app/open_rosalind.db \
  open-rosalind:latest
```

---

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | *(required)* | Your LLM provider key |
| `OPENROUTER_MODEL` | `google/gemma-4-26b-a4b-it` | Any OpenRouter model id |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | Override for self-hosted vLLM, OpenAI, Azure, etc. |
| `PORT` | `80` | Port inside container |
| `HOST` | `0.0.0.0` | Listen address |

The image speaks the **OpenAI Chat Completions** API, so `OPENROUTER_BASE_URL` works with any compatible endpoint:

- **OpenAI**: `https://api.openai.com/v1` + `OPENROUTER_API_KEY=sk-...`
- **Self-hosted vLLM**: `http://your-vllm-host:8000/v1`
- **Azure OpenAI**: full endpoint URL + matching key
- **Local Ollama** (via litellm proxy): `http://litellm:4000/v1`

---

## Persistent volumes

The container mounts these dirs out so user data survives rebuilds:

| Path inside container | Purpose |
|---|---|
| `/app/open_rosalind.db` | SQLite (users, sessions, messages, traces) |
| `/app/sessions/` | Per-session JSONL event logs |
| `/app/traces/` | Per-call JSONL trace audit log |
| `/app/task_traces/` | Multi-step task traces |

---

## Healthcheck

The container exposes `/api/health` and Docker checks it every 30 s:

```bash
docker inspect --format='{{.State.Health.Status}}' open-rosalind
# → healthy
```

---

## Image size

Approximate sizes (build cache cold):

| Stage | Size |
|---|---|
| `node:20-alpine` builder | ~250 MB (discarded) |
| `python:3.12-slim` runtime | ~180 MB base |
| Final image | ~400 MB (Python deps + UI bundle) |
