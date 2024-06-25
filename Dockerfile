FROM ghcr.io/astral-sh/uv:0.2.15 AS uv
FROM python:3.12-slim

WORKDIR /app

COPY requirements.lock ./

# comment out editable requirements, since they're not permitted in constraint files
RUN sed -ir 's/^-e /# -e /g' requirements.lock

COPY common/pyproject.toml common/
COPY common/src/ghutils/common/__version__.py common/src/ghutils/common/
RUN mkdir -p common/src/ghutils/common && touch common/src/ghutils/common/__init__.py

COPY bot/pyproject.toml bot/
RUN mkdir -p bot/src/ghutils/bot && touch bot/src/ghutils/bot/__init__.py

# https://github.com/astral-sh/uv/blob/main/docs/docker.md
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    PYTHONDONTWRITEBYTECODE=1 \
    uv pip install --system \
    --constraint requirements.lock \
    -e bot -e common

COPY common/ common/
COPY bot/ bot/

# NOTE: this must be a list, otherwise signals (eg. SIGINT) are not forwarded to the bot
CMD ["python", "-m", "ghutils.bot.app"]

# HEALTHCHECK \
#     --interval=15m \
#     --timeout=30s \
#     --start-period=2m \
#     --start-interval=1m \
#     --retries=1 \
#     CMD python scripts/bot/health_check.py
