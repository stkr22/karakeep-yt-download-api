# Application image: FastAPI webhook receiver that runs yt-dlp (needs ffmpeg for merging/thumbnails).

# Build stage: Python 3.14.7-trixie
FROM docker.io/library/python:3.14.7-trixie@sha256:20f4b272cb5d0f462c84645f8127d82e6fcfdc4006f4dd7f8859a5be4d5ef7a5 AS build-python

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

# Must satisfy `required-version` in pyproject.toml ([tool.uv]).
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-install-project --no-dev

# README.md and LICENSE are read by the uv_build backend (readme, license-files).
COPY src/ src/
COPY README.md LICENSE ./
RUN --mount=type=cache,target=/root/.cache \
    uv sync --locked --no-dev

# Runtime stage: Python 3.14.7-slim-trixie
FROM docker.io/library/python:3.14.7-slim-trixie@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# UID/GID 1001 should match the owner of the NFS export (or set pod fsGroup/runAsUser in the chart).
RUN addgroup --system --gid 1001 appuser && adduser --system --uid 1001 --no-create-home --ingroup appuser appuser

WORKDIR /app
COPY --from=build-python /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

EXPOSE 8000
CMD ["uvicorn", "karakeep_yt_download_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
