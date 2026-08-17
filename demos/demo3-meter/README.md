# Demo 3 — MEASURE your own Claude Code cost

A local, **stdlib-only** FinOps meter over Claude Code's local session logs. It
derives tokens → dollars for every session you've run — measuring subagent
delegation cost exactly (not estimating it), and modeling in-session skill cost at
user-turn granularity — then ranks sessions by cost and skills/subagents by usage.

Same premise as the original GitHub Copilot version of this demo: *the bill is
already in your logs; you don't need a new SaaS to see it.* Ported to Claude Code,
the story gets stronger — Claude's logs carry real per-message token usage and
subagent work runs in its own log file, so this meter can measure things the
Copilot version could only model.

> ⚠️ **Read this before you present a single number:** every $ figure here is a
> **notional, API-equivalent cost** — what your token usage would cost at
> Anthropic's per-token API rates. It is **not your subscription bill**. Most
> Claude Code users are on a flat-rate plan. See `VALIDATION.md` and the banner on
> the dashboard itself.
>
> **Privacy:** this reads only your **local** `~/.claude/projects` logs and writes
> everything locally. Generated artifacts (`finops.db`, `dashboard_data.json`,
> `dashboard.html`) contain your real session data and are **gitignored** — they
> never get committed or pushed.

## Run it (<1 min, no dependencies)

```bash
cd demos/demo3-meter
python3 -m unittest test_finops_core.py -v   # sanity-check the math (synthetic fixtures)
python3 build_db.py                          # build finops.db from ~/.claude/projects
python3 export_dashboard.py                  # emit dashboard_data.json + dashboard.html
open dashboard.html                          # (Windows: start dashboard.html)
```

Override the log location if needed:

```bash
CLAUDE_PROJECTS_DIR=/custom/path python3 build_db.py
```

## Data source

Claude Code writes a JSONL transcript per session under `~/.claude/projects/`, plus
a separate JSONL file per delegated subagent under a `subagents/` subfolder, each
with a `.meta.json` sidecar naming the subagent type. This meter reads only that —
no telemetry, no API calls, no server.

## What it computes

Pricing table lives in `finops_core.py` (`PRICING_RULES`) — current per-model rates
plus a Sonnet 5 introductory-pricing cutoff (2026-08-31). Cache tokens price off the
model's input rate: cache-read ≈0.10×, cache-write ≈1.25× (5-min TTL, the default)
or ≈2.00× (1-hour TTL, read from the log's cache breakdown when present). Models
this table doesn't recognize are counted in tokens with `usd = null` — never a
guessed price.

## Schema (`finops.db`)

- `sessions` — per-session totals: tokens, dollars, message count, unpriced-message
  count. **Measured.**
- `session_models` — per-session, per-model breakdown. **Measured.**
- `session_subagents` — per-subagent-invocation tokens/dollars, with a
  `label_confidence` column (`matched` / `matched (timestamp fallback)` /
  `unlabeled`) showing how the subagent type was identified. **Measured cost,
  best-effort label.**
- `session_skill_turns` — in-session Skill-tool cost, attributed per user turn.
  **Modeled**, not measured — see `VALIDATION.md`.
- `session_tools` — invocation counts for tools, skills, and subagent calls
  (`kind` column distinguishes them). Counts only, no dollar figure.
- `etl_metadata` — scan stats: files scanned, billable messages found, which
  models had no pricing data, and which unrecognized entry types were skipped.

## Dashboard

`dashboard.html` is self-contained — data is embedded inline, so it opens directly
from the filesystem with no local server. `dashboard_data.json` is written
alongside it as a separate, reusable artifact (e.g. for the advanced OTel
cross-check tool — see `advanced/`).

## Honest limitations — read `VALIDATION.md`

Every number this tool produces is labeled MEASURED, MODELED, or NOT DERIVABLE, with
the reasoning and the sanity checks run against real data during development.
Presenting any number from this tool without that context misrepresents what it
actually shows.

## Credits

Ported from `danielmeppiel/finops-workshop`'s Demo 3 (GitHub Copilot). Pricing data
and Claude Code local log/telemetry format researched against Anthropic's public
documentation and a real, heavily-used Claude Code install.
