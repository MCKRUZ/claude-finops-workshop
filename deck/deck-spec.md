# Deck spec — FinOps for Agentic Coding (Claude Code)

Source of truth for the built deck in `../docs/`. If the built HTML and this spec
disagree, this file wins — update the HTML to match, not the reverse.

## The spine

```
Hook(1) → Reframe(2) → Why-not-dev(3) +DEMO1 → Lifecycle loop(4)
        → Pools(5) → Tooling(6) +DEMO2 → Meter +DEMO3 → Playbook(7) → Exercise
```

Same 3-act structure as the original Copilot deck. Tools swapped:

| Original (Copilot) | This deck (Claude Code) |
|---|---|
| GitHub Copilot App | Claude Code |
| GitHub Agentic Workflows | Claude Code hooks + plugin marketplace |
| `apm` (Agent Package Manager) | Claude Code's native plugin/skill system (`apm` mentioned as a supplementary path, not depended on) |
| `genesis` | `genesis` — unchanged, already supports Claude Code |

## The three demos

1. **DESIGN** (`demos/demo1-design/`) — `genesis` designs a cost-aware agentic
   workflow: explore once at frontier cost (Claude Opus 5 / Fable 5), then codify
   the cheap, repeatable loop (Sonnet 5 / Haiku 4.5).
2. **GOVERN** (`demos/demo2-govern/`) — a Claude Code plugin: a pinned, versioned
   skill plus a spend-gate hook. "A governed, reusable workflow" — done with native
   Claude Code primitives, not a Copilot-shaped workaround.
3. **MEASURE** (`demos/demo3-meter/`) — the meter reads **your own** Claude Code
   logs. *"It's already in your logs. No new SaaS."* Stronger claim than the
   original here: subagent delegation cost is **measured**, not modeled — Claude's
   logs carry real per-message usage where Copilot's don't.

**Tools shown:** Claude Code · Claude Code plugins/hooks · `genesis`.

## Number discipline — the one hard rule

**Never present a number this deck didn't measure live, on this machine, in front
of this room.** The original deck's own numbers ($4.81 / $33.79 / $41.01) are
Copilot-metered facts specific to that demo run — they do not transfer to Claude
Code, and copying them into this deck would be presenting a fabricated number as a
measured one. Every cost-comparison slide in this deck (`s06-money.html`) ships
with `[illustrative — regenerate locally]` placeholders and an explicit
instruction: run `demos/demo3-meter/` against your own logs before presenting, and
replace the placeholders with what you actually measured.

The dashboard mirrors this discipline: session/model cost is **measured**;
in-session skill cost is an explicit **estimate**. See
`demos/demo3-meter/VALIDATION.md`.

**Second hard rule, specific to this port:** every dollar figure — in the deck, on
the dashboard, everywhere — is a *notional, API-equivalent* cost, not a
subscription bill. State this on the money slide explicitly; don't let a
$30-vs-$4 comparison read as "you'll save $26" for an audience mostly not paying
per token in the first place.

## Slide-by-slide (maps to `docs/slides/*.html`)

| File | Content |
|---|---|
| `cover.html` | Title, hook line. |
| `intro.html` | Who this is for (AI Champions, platform leads, admins), what it isn't (not dev basics). |
| `s01-number.html` | The hook: a big, real, illustrative-until-you-measure-it number. |
| `s02-reframe.html` | "Your bill is a variance you engineer" — reframe cost from a line-item to a design decision. |
| `s03-why-not-dev.html` | Why this isn't "learn to prompt better" — it's an operating-model problem. **+ launch Demo 1.** |
| `s04-demo-design.html` | Demo 1 walkthrough slide: explore once, codify cheap. |
| `s05-lifecycle-loop.html` | The lifecycle: design → govern → measure → feed back into design. |
| `s06-money.html` | The cost-comparison table — illustrative placeholders, explicit "regenerate locally" instruction, API-equivalent-cost caveat. |
| `s07-tooling.html` | The tool map: Claude Code, plugins/hooks, genesis. **+ launch Demo 2.** |
| `s08-demo-govern.html` | Demo 2 walkthrough: pinned skill + spend-gate hook. |
| `s09-demo-measure.html` | Demo 3 walkthrough: the meter, run live against the room's own logs if anyone volunteers. **Measured vs. modeled, said out loud.** |
| `s10-playbook.html` | The three plays: tier models, pool the spend, codify the top loops. |
| `s11-exercise.html` | Room exercise: pick one repeated task, sketch its explore-once/codify-cheap split. |
| `resources.html` | Links: this repo, `genesis`, Claude Code plugin docs, Anthropic pricing page. |

## Facilitator notes

See `../docs/facilitator-guide.md` for timing, the live-meter demo script, and
what to do if a volunteer's logs are empty (offer the presenter's own, pre-run).
