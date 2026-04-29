# syntax=docker/dockerfile:1

# === Stage 1: Build React UI ===
FROM node:20-alpine AS web-builder
WORKDIR /web-react

# Copy only what's needed to install deps for layer caching
COPY web-react/package.json web-react/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# Copy source
COPY web-react/ ./
# vite.config.js outDir is '../web/dist'; create that path so build doesn't fail
RUN mkdir -p /web/dist
RUN npm run build
# Output now lives in /web/dist (one level up from /web-react)


# === Stage 2: Runtime ===
FROM python:3.12-slim AS runtime

# System deps (curl for healthcheck, libgomp/libstdc++ if BioPython needs them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps — install first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.110" \
    "uvicorn>=0.29" \
    "openai>=1.30" \
    "requests>=2.31" \
    "pydantic>=2.0" \
    "biopython>=1.83" \
    "pyyaml>=6.0"

# Copy application code
COPY open_rosalind/ ./open_rosalind/
COPY configs/ ./configs/

# Copy built web UI from stage 1
COPY --from=web-builder /web/dist ./web/dist

# Create runtime dirs (sessions / traces / sqlite db)
RUN mkdir -p /app/sessions /app/traces /app/task_traces

# Default config: use port 80 inside container, accept env-var overrides
ENV PORT=80 \
    HOST=0.0.0.0 \
    OPENROUTER_API_KEY="" \
    OPENROUTER_MODEL="google/gemma-4-26b-a4b-it" \
    OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

EXPOSE 80

# Healthcheck (use shell form so $PORT expands)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f "http://127.0.0.1:${PORT}/api/health" || exit 1

# Run as the open-rosalind CLI (picks up PORT/HOST env vars)
CMD ["python", "-m", "open_rosalind.cli", "serve"]
