FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    SQLITE_CACHE_PATH=/data/dictionary-cache.sqlite3 \
    VOCABULARY_DB_PATH=/data/dictionary-vocabulary.sqlite3

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN pip install --no-cache-dir .
RUN mkdir -p /data && chown 10001:10001 /data

EXPOSE 8000
USER 10001:10001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
