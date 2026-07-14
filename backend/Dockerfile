FROM python:3.13-slim AS builder

WORKDIR /app

ARG MAXMIND_LICENSE_KEY=""

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

COPY pyproject.toml README.md* ./
COPY src/ src/

RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv/bin/python --no-cache .

RUN mkdir -p /opt/geoip \
    && if [ -n "$MAXMIND_LICENSE_KEY" ]; then \
         curl -sSL "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz" \
           | tar -xz -C /tmp && \
         mv /tmp/GeoLite2-City_*/GeoLite2-City.mmdb /opt/geoip/GeoLite2-City.mmdb && \
         rm -rf /tmp/GeoLite2-City_*; \
       else \
         echo "Fetching GeoLite2-City from community mirror (P3TERX/GeoLite.mmdb)" && \
         curl -sSL "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb" \
           -o /opt/geoip/GeoLite2-City.mmdb && \
         test -s /opt/geoip/GeoLite2-City.mmdb || \
           (echo "GeoIP mirror fetch failed — runtime fallback to no-geo" && \
            rm -f /opt/geoip/GeoLite2-City.mmdb && \
            touch /opt/geoip/.placeholder); \
       fi

FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /opt/geoip /opt/geoip
COPY --chown=app:app src/ src/
COPY --chown=app:app alembic/ alembic/
COPY --chown=app:app alembic.ini .

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "std_cards.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=10.42.0.0/16,10.43.0.0/16,127.0.0.1"]
