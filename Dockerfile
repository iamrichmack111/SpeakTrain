FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SPEAKTRAIN_HOST=0.0.0.0 \
    SPEAKTRAIN_PORT=8095 \
    SPEAKTRAIN_DATABASE=/data/speaktrain.sqlite3

WORKDIR /app

RUN addgroup --system speaktrain && adduser --system --ingroup speaktrain speaktrain \
    && mkdir -p /data && chown speaktrain:speaktrain /data

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY speaktrain ./speaktrain

USER speaktrain
EXPOSE 8095
VOLUME ["/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8095/healthz', timeout=3)"

CMD ["sh", "-c", "gunicorn --workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4} --bind 0.0.0.0:${SPEAKTRAIN_PORT:-8095} --access-logfile - app:app"]
