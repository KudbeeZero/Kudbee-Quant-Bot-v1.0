# Fly.io image for the Kudbee Quant FastAPI app (dashboard + /api, incl. the
# TradingView alert webhook). Runbook: docs/HOSTING.md.
FROM python:3.11-slim

# Faster, quieter, reproducible Python in a container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install deps first so the layer caches across code-only changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# App code + the JSON data the API reads (journal, research ledgers). The
# .dockerignore keeps the parquet OHLCV caches + tests/website out of the image;
# the journal is a mirror refreshed by `fly deploy` (see .github/workflows/fly-deploy.yml).
COPY kudbee_quant ./kudbee_quant
COPY config ./config
COPY data ./data

# Fly routes public traffic to this internal port (see fly.toml [http_service]).
ENV PORT=8080
EXPOSE 8080

# One worker: the app holds process-local state (the in-memory rate-limiter,
# run-job registry) that must not be split across workers. Vertical scale only.
CMD ["sh", "-c", "uvicorn kudbee_quant.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
