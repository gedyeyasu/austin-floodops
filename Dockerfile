# Austin FloodOps - Production container for NemoClaw/OpenShell + FastAPI
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8080 \
    HOST=0.0.0.0

WORKDIR /app

# System deps: curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Copy dependency manifests first for layer caching
COPY pyproject.toml README.md ./
COPY app/__init__.py app/__init__.py

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[texas,test]"

# Copy full source
COPY app/ app/
COPY data/replay/ data/replay/
COPY openshell/ openshell/
COPY supabase/ supabase/
COPY scripts/ scripts/

# Create writable runtime paths for a non-root container. OpenShift assigns an
# arbitrary user ID, so group 0 must be able to write the application volume.
RUN useradd --uid 1001 --gid 0 --no-create-home --shell /usr/sbin/nologin floodops && \
    mkdir -p /app/data /tmp && \
    chgrp -R 0 /app /tmp && \
    chmod -R g=u /app /tmp

# Healthcheck hits /health which probes NWS/USGS/Nemotron/Kafka/Supabase/OpenShell gates
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -f http://127.0.0.1:8080/health || exit 1

EXPOSE 8080

USER 1001

# Run via uvicorn. Lifespan starts HeartbeatEngine polling NWS+USGS (+Austin open data) every POLL_SECONDS.
# NemoClaw should mount this container through OpenShell sandbox with openshell/austin-floodops.yaml policy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
