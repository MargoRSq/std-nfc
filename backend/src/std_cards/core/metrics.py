from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

http_requests = Counter(
    "std_cards_http_requests_total",
    "HTTP requests",
    ["method", "endpoint", "status"],
)
http_duration = Histogram(
    "std_cards_http_duration_seconds",
    "Request duration",
    ["endpoint"],
)
scan_events_published = Counter(
    "std_cards_scan_events_published_total",
    "Scan events published to NATS",
)
import_jobs_processed = Counter(
    "std_cards_import_jobs_processed_total",
    "Import jobs processed",
    ["status"],
)
login_attempts = Counter(
    "std_cards_login_attempts_total",
    "Login attempts",
    ["result"],
)


def setup_metrics(app: FastAPI) -> None:
    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
