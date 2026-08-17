# Advanced — OTel cross-check (optional)

The local-log meter (`../build_db.py`) **models** in-session skill cost by attributing
it at user-turn granularity — a reasoned estimate, not a measurement (see
`../VALIDATION.md`). Claude Code's official OpenTelemetry export carries a
`claude_code.cost.usage` metric that's natively tagged with the exact skill/agent
that caused it — **real, measured** per-skill dollars.

This directory is **not** a second dashboard pipeline — running both paths in
parallel risks them disagreeing on a number and undermining trust in both. It's a
one-time cross-check: run a single Claude Code session with telemetry pointed at a
tiny local receiver, capture what it says a skill actually cost, and diff that
against what the turn-attribution model guessed for the same skill.

## Setup

```bash
# 1. Start the receiver (leave this running in its own terminal)
python3 otel_bridge.py

# 2. In a second terminal, point Claude Code at it and start a fresh session
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_METRIC_EXPORT_INTERVAL=5000   # flush every 5s (default is 60s — too
                                           # slow to see anything in a short session)
claude
```

Do a short piece of work that invokes at least one skill, then exit. Do **not** set
`OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=cumulative` — this tool assumes
Claude Code's default (`delta`) and does not diff cumulative counters.

```bash
# 3. Rebuild the local-log meter's data for the same session
cd ..
python3 build_db.py && python3 export_dashboard.py
cd advanced

# 4. Compare
python3 compare_skill_cost.py
```

## What "good" looks like

The comparison is meaningful only if it's apples-to-apples: run it right after a
single fresh session, before anything else adds to the local meter's totals (which
are cumulative across every session it's ever seen). A close match between the OTel
column and the meter column is evidence the turn-attribution heuristic is a
reasonable approximation for your usage patterns. A persistent, large gap is a
concrete signal to revisit `build_db.py`'s skill-turn logic — not a reason to
distrust the (always-measured) session and subagent totals, which don't depend on
this at all.

## Files

- `otel_bridge.py` — the receiver. Stdlib only, no `opentelemetry` package
  dependency. Captures to `otel_capture.jsonl` (gitignored — contains your usage).
- `compare_skill_cost.py` — the diff report.
- `test_otel_bridge.py` — unit tests against synthetic OTLP payloads.

## Honest scoping

This was built to the documented OTLP/HTTP JSON format and verified end-to-end with
real HTTP requests (plain JSON, gzip, and the `partialSuccess` response Claude
Code's exporter needs to stop retrying) — but has not been exercised against a live
Claude Code telemetry export as part of this repo's development. Run the setup
above against your own install before presenting numbers from it. See
`otel_bridge.py`'s module docstring for the exact scope limits (delta-only
temporality, two metrics tracked).
