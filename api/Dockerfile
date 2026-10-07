# Multi-stage build for the FastAPI backend.
#
# Stage 1 installs dependencies (needs gcc + build headers for a few
# native deps like bcrypt / cryptography). Stage 2 is the runtime image
# — python:3.12-slim + only the installed site-packages and app source.
# No build tools, no test deps, no cache.

# ---- Stage 1: builder -------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Build deps for bcrypt/cryptography wheels that don't have manylinux
# binaries on ARM (Fly.io defaults to shared-cpu-1x on x86_64 but this
# keeps ARM builds honest too).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifests first so the pip layer caches across
# code-only rebuilds.
COPY pyproject.toml ./
COPY README.md* ./
COPY app/ ./app/

# Install into a virtualenv we can copy wholesale to the runtime stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel \
 && pip install .

# ---- Stage 2: runtime -------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# libpq5 is the only runtime lib we need from Postgres (asyncpg links
# statically against libcrypto; psycopg2-binary is dev-only). curl is
# useful for the health check container-side.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app app/ ./app/
COPY --chown=app:app alembic/ ./alembic/
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app pyproject.toml ./pyproject.toml

USER app

EXPOSE 8080

# The startup lifespan hook (see app/main.py) asserts the DB is at the
# expected Alembic head before the app accepts traffic — so `alembic
# upgrade head` MUST run first. Fly.io hosts run that as the release
# command declared in fly.toml. Local `docker run` users can pass
# `--entrypoint alembic ... upgrade head` before starting uvicorn.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
