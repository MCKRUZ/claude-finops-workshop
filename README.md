# FinOps for Agentic Coding — Claude Code Workshop

> **Your agentic bill is a variance you _engineer_, not a price you _negotiate_. The lever is the loop.**

A ~1-hour session for **AI Champions, platform leads, and admins** on controlling
Claude Code agentic-coding cost. Not developer basics — this is about **cost
control and the operating model**: designing reusable, cost-effective agent
workflows and governing the spend around them.

This is a Claude Code port of
[`danielmeppiel/finops-workshop`](https://github.com/danielmeppiel/finops-workshop),
originally built for GitHub Copilot. It is **not a 1:1 translation** — see
"What changed, and why" below.

Everything here is **self-contained and near-zero-build**: a minimalist HTML slide
deck you present from a browser, and one live demo that meters **your own** Claude
Code logs. No SaaS, no signup.

---

## TL;DR — what to do

| You want to… | Do this |
|---|---|
| **Present the deck** | Open `docs/index.html` in a browser (← / → to navigate, `F` to present fullscreen). |
| **Run the cost meter** | `cd demos/demo3-meter && python3 build_db.py && python3 export_dashboard.py && open dashboard.html` |
| **Install the governed workflow demo** | `/plugin marketplace add ./` then `/plugin install finops-govern@claude-finops-workshop` (from a `claude` session at this repo's root). |
| **Facilitate the room** | Read `docs/facilitator-guide.md`. |
| **Understand the narrative** | Read `deck/deck-spec.md` (the why) and `deck/deck-mockups.md` (slide-by-slide). |

---

## Repository map

| Path | What it is |
|---|---|
| `docs/` | The **built, presentable HTML deck** (`index.html` + `slides/`) — minimalist, 1280×720, offline. Plus `facilitator-guide.md`. |
| `deck/deck-spec.md` | Deck **source of truth**: the spine, the 3 acts, idea-slides + 3 demos, number discipline. |
| `deck/deck-mockups.md` | One minimalist ASCII mockup per slide — the design intent behind each built slide. |
| `demos/demo1-design/` | **Demo 1 — DESIGN.** Explore once at frontier cost, codify into a cheap repeatable loop. Uses [`genesis`](https://github.com/danielmeppiel/genesis), which already targets Claude Code — nothing to build. |
| `demos/demo2-govern/` | **Demo 2 — GOVERN.** A Claude Code plugin: a pinned, versioned skill (the reusable loop from Demo 1) gated by a spend-limit hook that reads Demo 3's local meter. |
| `demos/demo3-meter/` | **Demo 3 — MEASURE.** A stdlib-only meter that turns the Claude Code logs you already produce into real, measured dollar cost — including exact (not estimated) subagent delegation cost, an upgrade over the original Copilot version. |
| `.claude-plugin/marketplace.json` | Lists the Demo 2 plugin so it can be installed locally with `/plugin marketplace add`. |

---

## What changed, and why

Every mechanism in the original workshop is specific to GitHub Copilot: it parses
Copilot's private log format, prices tokens in Copilot's own "AI Units," and ships
its dashboard as a Copilot-only canvas extension via `apm`. Porting it meant finding
Claude Code's actual equivalent at each layer, not swapping labels:

- **DESIGN** needed no change — `genesis` already supports Claude Code.
- **GOVERN** moved from `apm` (which has an open bug in its Claude Code install
  path) to Claude Code's own plugin system — a version-pinned skill plus a
  policy-enforcing hook, both native mechanisms.
- **MEASURE** is a genuine upgrade, not just a port. Copilot's logs carry no
  per-message cost, so the original meter can only *model* (estimate) per-skill
  cost and says so explicitly. Claude Code's local logs embed the real Anthropic
  API usage on every turn, and subagent delegation runs in its own log file with
  its own real usage — so this meter **measures** subagent cost exactly, something
  the Copilot version structurally could not do. See
  `demos/demo3-meter/VALIDATION.md` for the full measured-vs-modeled breakdown.
- Claude Code has no "canvas" — there's no in-app embedded dashboard surface the
  way Copilot has. The dashboard opens as a local HTML file in a browser instead,
  which is also the original repo's own fallback when a canvas isn't available, so
  this isn't a downgrade.

---

## ⚠️ These are notional dollars, not your bill

Every dollar figure this workshop produces — dashboard, deck, demos — is a
**notional, API-equivalent cost**: what your token usage would cost at Anthropic's
published per-token API rates. Most Claude Code users are on a flat-rate
subscription (Pro/Max/Team), not pay-per-token billing. **This is not what you were
charged.** Presenting these numbers without that caveat teaches a false savings
story — see the banner on the dashboard itself, and `demos/demo3-meter/VALIDATION.md`.

---

## Number discipline (be honest)

The original deck leads with three metered numbers from its own Copilot-based
demos ($4.81 right-sized vs. $33.79 same-model-bad-loop vs. $41.01 premium-default).
Those numbers are Copilot-metered facts — they don't transfer. This deck ships with
clearly labeled **illustrative placeholders** instead, and an explicit instruction
to run Demo 3 against your own logs before presenting:

| Same high-value task | Cost | vs. right-sized |
|---|---|---|
| Right-sized loop (explore once → cheap loop) | `[illustrative — regenerate locally]` | 1× |
| Same model, bad loop (re-explores every run) | `[illustrative — regenerate locally]` | — |
| Premium default (highest tier everywhere) | `[illustrative — regenerate locally]` | — |

Lead with the **metered, replayable story** — never a headline multiplier you
can't reproduce live.

---

## Privacy — your telemetry stays local

The meter reads your local `~/.claude/projects` logs. Generated artifacts
(`finops.db`, `dashboard_data.json`, `dashboard.html`) contain **your real session
costs and usage** and are **gitignored** — they are never committed or pushed.
Regenerate them locally with `build_db.py` + `export_dashboard.py`.

---

## Credits

Ported from [`danielmeppiel/finops-workshop`](https://github.com/danielmeppiel/finops-workshop)
(GitHub Copilot original). Built on [`genesis`](https://github.com/danielmeppiel/genesis)
(workflow design, unchanged), Claude Code's native plugin/hooks system (governance),
and Claude Code's local session logs and official OpenTelemetry export (measurement).
