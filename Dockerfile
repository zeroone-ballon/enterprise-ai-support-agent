FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LIFECYCLE_DB_PATH=/app/state/support_agent.db

WORKDIR /app
RUN groupadd --system app && useradd --system --gid app --home /app app
COPY --from=ghcr.io/astral-sh/uv:0.8.13 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY data ./data
RUN uv sync --frozen --no-dev && mkdir -p /app/state && chown -R app:app /app

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD ["/app/.venv/bin/uvicorn", "support_agent.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
