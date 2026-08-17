# Facilitator guide

~60 minutes. Three live demos. Read `../deck/deck-spec.md` for the narrative spine
before your first run-through — this guide is timing and mechanics, not the "why."

## Before the room

1. **Run Demo 3 against your own machine at least a day before**, not live for the
   first time. `cd demos/demo3-meter && python3 -m unittest test_finops_core.py -v
   && python3 build_db.py && python3 export_dashboard.py`. Confirm `dashboard.html`
   opens and the numbers look sane — a mostly-empty `~/.claude/projects` produces a
   thin, unconvincing dashboard; if that's you, run a few real Claude Code sessions
   first (including at least one that delegates to a subagent, so the "measured
   subagent cost" story has something to show).
2. **Regenerate the `s06-money.html` numbers slide with your own figures.** The
   deck ships with `[regenerate locally]` placeholders — see "Number discipline" in
   `deck/deck-spec.md`. Never present the placeholders as-is.
3. **Install and test Demo 2** (`demos/demo2-govern/README.md`) — confirm
   `/plugin install` works and the budget gate actually blocks when you lower
   `FINOPS_DAILY_CAP_USD` below your measured spend.
4. Open `docs/index.html` in a browser and click through all 14 slides once. `F`
   toggles fullscreen.

## Timing (≈60 min)

| Segment | Slides | Minutes |
|---|---|---|
| Hook, reframe, why-not-dev | cover → s03 | 8 |
| Demo 1 — DESIGN | s04-demo-design | 7 |
| Lifecycle, money | s05, s06 | 8 |
| Demo 2 — GOVERN | s07, s08-demo-govern | 10 |
| Demo 3 — MEASURE | s09-demo-measure | 12 |
| Playbook, exercise | s10, s11 | 12 |
| Resources, close | resources | 3 |

## Running Demo 3 live

The strongest moment in the workshop is running the meter against a volunteer's
own machine, not a pre-baked demo. Script:

1. Ask for a volunteer with Claude Code installed and some real usage history.
2. Have them run, on their own laptop, screen-shared:
   ```bash
   cd demos/demo3-meter
   python3 build_db.py
   python3 export_dashboard.py
   open dashboard.html
   ```
3. Point at the disclosure banner first, out loud, before any number: *"This is
   API-equivalent cost, not your bill."*
4. Walk the sections in this order: summary cards → per-model → top sessions →
   subagent delegation (say the word "measured" here, explicitly) → in-session
   skills (say the word "modeled" here, explicitly, and why).

**If the volunteer's logs are empty or thin:** don't force it live — switch to your
own pre-run dashboard (step 1 above) and say so plainly: *"here's mine, from
running this workshop's own demos."* An empty dashboard reads as the tool being
broken, not as an honest edge case, so don't let that be the room's first
impression of it.

## Common questions

- **"Is this what I'm actually being charged?"** No — see the disclosure banner.
  Most attendees are on a subscription. This is the API-equivalent-cost lens, useful
  for understanding *relative* cost between loops, not for reconciling an invoice.
- **"Why doesn't it show exact dollars for every skill?"** Because Claude Code's
  logs don't carry a closing event for in-session skill use — the meter is honest
  about modeling that slice rather than fabricating precision. See
  `demos/demo3-meter/VALIDATION.md`. Subagent delegation, in contrast, *is* exact —
  point this contrast out, it's the strongest technical claim in the demo.
- **"Does this work with `apm`?"** `apm` claims Claude Code support but has an open
  bug in that exact path as of this writing — Demo 2 uses Claude Code's native
  plugin system instead. Mention `apm` as a name attendees may recognize from the
  GitHub Copilot ecosystem, not as something this workshop depends on.
