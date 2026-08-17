"""otel_bridge.py — a minimal local OTLP/HTTP-JSON receiver for Claude Code's
official telemetry, used as a CROSS-CHECK against this meter's modeled
in-session skill-cost attribution, not as a second ingest pipeline.

Why a cross-check and not a parallel dashboard: Claude Code's OTel export
carries a `claude_code.cost.usage` metric tagged with the exact skill/agent
that caused it — real, measured per-skill dollars, solving the modeling gap
that `session_skill_turns` in the local-log path has to estimate. But
shipping OTel as a second full ingest path risks the two paths disagreeing
on a number and destroying trust in both. Instead: run ONE Claude Code
session with telemetry on, capture what it says a skill actually cost, and
diff that against what build_db.py's turn-attribution model guessed for the
same session. See README.md in this directory for the full walkthrough.

SCOPE, read before relying on this:
- Assumes the DEFAULT delta temporality
  (OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=delta, which is Claude
  Code's default — do not override it to "cumulative", this tool does not
  diff cumulative counters).
- Only two metrics are captured: claude_code.cost.usage and
  claude_code.token.usage. Everything else Claude Code exports is ignored.
- Written to the documented OTLP/HTTP JSON wire format, unit-tested against
  synthetic payloads (test_otel_bridge.py), and smoke-tested end-to-end with
  real HTTP requests (plain JSON, gzip-encoded, and an unsupported-method
  request) — all confirmed working during development. What is NOT verified:
  a live Claude Code process actually exporting to this receiver. Run the
  walkthrough in README.md against your own install before trusting the
  numbers it captures.
- Stdlib only. No dependency on the `opentelemetry` Python package.
"""

from __future__ import annotations

import gzip
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

CAPTURE_PATH = Path(__file__).parent / "otel_capture.jsonl"
TRACKED_METRICS = {"claude_code.cost.usage", "claude_code.token.usage"}

_capture_lock = threading.Lock()


def _attr_value(value_obj: dict) -> object:
    """Unwrap an OTLP AnyValue JSON object to a plain Python value."""
    if "stringValue" in value_obj:
        return value_obj["stringValue"]
    if "intValue" in value_obj:
        # OTLP encodes int64 as a JSON string to avoid precision loss.
        try:
            return int(value_obj["intValue"])
        except (TypeError, ValueError):
            return value_obj["intValue"]
    if "doubleValue" in value_obj:
        return value_obj["doubleValue"]
    if "boolValue" in value_obj:
        return value_obj["boolValue"]
    return None


def _attrs_to_dict(attributes: list) -> dict:
    out = {}
    for kv in attributes or []:
        key = kv.get("key")
        val = kv.get("value") or {}
        if key:
            out[key] = _attr_value(val)
    return out


def _data_point_value(dp: dict) -> Optional[float]:
    if "asDouble" in dp:
        return dp["asDouble"]
    if "asInt" in dp:
        try:
            return float(dp["asInt"])
        except (TypeError, ValueError):
            return None
    return None


def extract_records(otlp_payload: dict) -> list[dict]:
    """Flatten an OTLP ExportMetricsServiceRequest JSON body into a list of
    {"metric": name, "value": float, "attributes": {...}, "time_unix_nano": str}
    records, keeping only TRACKED_METRICS. Handles both `sum` and `gauge`
    metric shapes (Claude Code's cost/token metrics are sums)."""
    records = []
    for resource_metrics in otlp_payload.get("resourceMetrics", []) or []:
        for scope_metrics in resource_metrics.get("scopeMetrics", []) or []:
            for metric in scope_metrics.get("metrics", []) or []:
                name = metric.get("name")
                if name not in TRACKED_METRICS:
                    continue
                container = metric.get("sum") or metric.get("gauge") or {}
                for dp in container.get("dataPoints", []) or []:
                    value = _data_point_value(dp)
                    if value is None:
                        continue
                    records.append(
                        {
                            "metric": name,
                            "value": value,
                            "attributes": _attrs_to_dict(dp.get("attributes")),
                            "time_unix_nano": dp.get("timeUnixNano"),
                        }
                    )
    return records


def append_capture(records: list[dict], path: Path = CAPTURE_PATH) -> None:
    if not records:
        return
    with _capture_lock:
        with path.open("a", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")


class _OtlpHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # quieter default logging
        sys.stderr.write(f"[otel_bridge] {format % args}\n")

    def do_POST(self):
        if self.path not in ("/v1/metrics", "/v1/metrics/"):
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        if self.headers.get("Content-Encoding", "").lower() == "gzip":
            try:
                body = gzip.decompress(body)
            except OSError:
                self.send_response(400)
                self.end_headers()
                return

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_response(400)
            self.end_headers()
            return

        records = extract_records(payload)
        append_capture(records)

        # A valid, empty partialSuccess response tells the exporter the
        # batch succeeded — without this the SDK will retry indefinitely.
        response = json.dumps({"partialSuccess": {}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        if records:
            print(f"[otel_bridge] captured {len(records)} data point(s)", file=sys.stderr)


def run(host: str = "127.0.0.1", port: int = 4318) -> None:
    server = ThreadingHTTPServer((host, port), _OtlpHandler)
    print(f"[otel_bridge] listening on http://{host}:{port}/v1/metrics")
    print(f"[otel_bridge] capturing claude_code.cost.usage / claude_code.token.usage to {CAPTURE_PATH}")
    print("[otel_bridge] point Claude Code at this receiver with:")
    print("    export CLAUDE_CODE_ENABLE_TELEMETRY=1")
    print("    export OTEL_METRICS_EXPORTER=otlp")
    print(f"    export OTEL_EXPORTER_OTLP_ENDPOINT=http://{host}:{port}")
    print("    export OTEL_EXPORTER_OTLP_PROTOCOL=http/json")
    print("    export OTEL_METRIC_EXPORT_INTERVAL=5000   # flush every 5s instead of the 60s default")
    print("Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
