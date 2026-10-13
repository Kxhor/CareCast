# Multi-stage production Dockerfile for CareCast (TRD §10)
# Hardened, non-root user, minimal attack surface

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root system user and group
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -M appuser

# Copy installed python wheels from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

# Copy application source, static assets, configuration, and baked SQLite DB
COPY --chown=appuser:appgroup carecast /app/carecast
COPY --chown=appuser:appgroup web /app/web
COPY --chown=appuser:appgroup config /app/config
COPY --chown=appuser:appgroup data/carecast.db /app/data/carecast.db

# Ensure appuser owns data directory (read-only SQLite mount)
RUN chown -R appuser:appgroup /app/data

# Switch to non-root user
USER 10001:10001

# Production environment defaults
ENV CARECAST_ENV=prod \
    CARECAST_ENABLE_DOCS=0 \
    CARECAST_DB_PATH=/app/data/carecast.db

EXPOSE 8000

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3).status == 200 else 1)" || exit 1

# Production server entrypoint
CMD ["python", "-m", "uvicorn", "carecast.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
