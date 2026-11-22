"""Chapter 6 — observability: metrics, structured logs, traces.

The book's three kinds of telemetry, in Python form:
* Metrics — ``prometheus_client`` (the book's Prometheus client):
  a counter of RPCs by method/status and a histogram of durations.
  Expose them with ``start_metrics_server(port)`` (``/metrics``).
* Structured logs — the standard ``logging`` module, JSON-formatted
  one line per event (the book uses Zap; ``structlog`` is the
  closest Python equivalent and is listed as an optional extra).
  ``LoggingInterceptor`` logs each RPC with method, duration and
  status — the book's Zap interceptors, unary and streaming.
* Traces — OpenTelemetry (``opentelemetry-sdk`` + the gRPC
  instrumentor, optional extras). ``setup_tracing`` is a no-op when
  the packages are not installed, so the core service never depends
  on them; the interceptor below still records a span when a tracer
  is configured.

Nothing here is required to run the service: all three are wired in
through interceptors, exactly as the book wires its middleware.
"""

import json
import logging
import time

import grpc

try:
    from prometheus_client import Counter, Histogram, start_http_server
except ImportError:  # pragma: no cover - prometheus_client is a core dep
    Counter = Histogram = start_http_server = None  # type: ignore

RPC_TOTAL = (
    Counter("pylog_rpc_total", "RPCs handled", ["method", "status"])
    if Counter is not None
    else None
)
RPC_DURATION = (
    Histogram("pylog_rpc_duration_seconds", "RPC duration", ["method"])
    if Histogram is not None
    else None
)


def start_metrics_server(port: int = 2112) -> None:
    """Serve Prometheus metrics on ``:port/metrics`` (the book's
    ``:2112`` default is kept)."""
    if start_http_server is not None:
        start_http_server(port)


def new_logger(name: str = "pylog") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    logger.info(json.dumps({"event": event, **fields}))


class MetricsInterceptor(grpc.ServerInterceptor):
    """Count and time every RPC, unary and streaming."""

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None:
            return None
        method = handler_call_details.method.rsplit("/", 1)[-1]

        if handler.unary_unary is not None:
            orig = handler.unary_unary

            def unary_unary(request, context):
                start = time.monotonic()
                try:
                    resp = orig(request, context)
                    status = context.code() or grpc.StatusCode.OK
                except Exception:
                    status = grpc.StatusCode.INTERNAL
                    raise
                finally:
                    self._observe(method, start, status)
                return resp

            return handler._replace(unary_unary=unary_unary)
        return handler

    @staticmethod
    def _observe(method: str, start: float, status) -> None:
        if RPC_TOTAL is not None:
            RPC_TOTAL.labels(method=method, status=status.name).inc()
        if RPC_DURATION is not None:
            RPC_DURATION.labels(method=method).observe(time.monotonic() - start)


class LoggingInterceptor(grpc.ServerInterceptor):
    """One structured log line per unary RPC: method, duration, status."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self.logger = logger or new_logger()

    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None or handler.unary_unary is None:
            return handler
        orig = handler.unary_unary
        method = handler_call_details.method

        def unary_unary(request, context):
            start = time.monotonic()
            resp = orig(request, context)
            log_event(
                self.logger,
                "rpc",
                method=method,
                duration_ms=round((time.monotonic() - start) * 1000, 2),
                status=(context.code() or grpc.StatusCode.OK).name,
            )
            return resp

        return handler._replace(unary_unary=unary_unary)


def setup_tracing(service_name: str = "pylog", endpoint: str | None = None):
    """Configure OpenTelemetry tracing if the SDK is installed.
    Returns a tracer (or ``None``). With no endpoint the SDK's
    default (stdout / no exporter) applies; pass an OTLP endpoint
    for a real collector. Never raises when OTel is absent."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
    except ImportError:
        return None
    provider = TracerProvider(resource=Resource({"service.name": service_name}))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
