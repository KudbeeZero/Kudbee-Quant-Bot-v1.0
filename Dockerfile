# Hosted Kudbee API: dashboard + TradingView alert webhook (docs/DEPLOY.md).
# Journal state does NOT live in this image — it lives in a repo clone on the
# persistent volume (see deploy/entrypoint.sh + deploy/journal_sync.py).
# Overridable for registries that mirror Docker Hub (rate limits), e.g.
#   --build-arg BASE_IMAGE=public.ecr.aws/docker/library/python:3.11-slim
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

# git: required by the journal-sync sidecar (clone/pull/push of the journal).
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY kudbee_quant/ kudbee_quant/
RUN pip install --no-cache-dir --no-deps .
COPY deploy/ deploy/

RUN useradd -m kudbee
USER kudbee

EXPOSE 8080
CMD ["sh", "/app/deploy/entrypoint.sh"]
