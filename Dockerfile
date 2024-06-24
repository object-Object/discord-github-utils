FROM ghcr.io/astral-sh/uv AS uv

FROM python:3.12-slim

COPY --from=uv /uv /usr/bin/uv

WORKDIR /app

COPY requirements.lock ./

# comment out editable requirements, since they're not permitted in constraint files
RUN sed -ir 's/^-e /# -e /g' requirements.lock

COPY bot/pyproject.toml bot/
RUN mkdir -p bot/src/dgu_bot && touch bot/src/dgu_bot/__init__.py

COPY common/pyproject.toml common/
COPY common/src/dgu_common/__version__.py common/src/dgu_common/
RUN mkdir -p common/src/dgu_common && touch common/src/dgu_common/__init__.py

RUN --mount=type=cache,target=/root/.cache/uv \
    PYTHONDONTWRITEBYTECODE=1 \
    uv pip install --system \
    --constraint requirements.lock \
    -e bot -e common

COPY bot/ bot/
COPY common/ common/

CMD python -m dgu_bot.app

# HEALTHCHECK \
#     --interval=15m \
#     --timeout=30s \
#     --start-period=2m \
#     --start-interval=1m \
#     --retries=1 \
#     CMD python scripts/bot/health_check.py
