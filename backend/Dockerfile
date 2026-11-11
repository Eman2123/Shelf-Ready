FROM python:3.11-slim
WORKDIR /srv
COPY pyproject.toml alembic.ini ./
COPY app ./app
RUN pip install --no-cache-dir .
EXPOSE 8000
# Apply migrations (no-op without DATABASE_URL, e.g. demo mode), then serve. $PORT is set by hosts
# such as Render and Fly; it falls back to 8000 locally.
CMD ["sh", "-c", "if [ -n \"$DATABASE_URL\" ]; then alembic upgrade head; fi && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
