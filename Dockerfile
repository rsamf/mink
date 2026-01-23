FROM ghcr.io/astral-sh/uv:python3.10-trixie-slim AS builder

WORKDIR /build

COPY pyproject.toml uv.lock .
RUN uv sync --python-platform x86_64-manylinux_2_38 --no-dev --frozen

# Runtime
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxcb1 \
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
