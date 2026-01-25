FROM ghcr.io/astral-sh/uv:python3.10-trixie-slim AS builder

ARG sync_options="--extra server"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY pyproject.toml uv.lock ./
RUN uv sync --python-platform x86_64-manylinux_2_38 --frozen ${sync_options}

# Runtime
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/.venv /app/.venv

COPY mink mink
COPY config config

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="/app"

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "mink.main:app", "--host", "0.0.0.0", "--port", "8000"]
