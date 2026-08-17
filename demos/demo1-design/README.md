# Demo 1 — DESIGN a cost-aware agentic workflow

**Nothing to port here.** The original GitHub Copilot demo uses
[`genesis`](https://github.com/danielmeppiel/genesis) — an architectural layer for
designing multi-agent, multi-skill workflows as portable, versioned markdown — and
`genesis` already lists Claude Code among its 40+ supported target harnesses. This
is the one demo in the workshop that needed no adaptation at all.

## The pattern

> Explore once, at the cost the problem actually needs to be *understood*. Codify
> what you learned into fixed steps a cheaper model can *execute* every time after.

Two spends, two different jobs:

| Phase | What it's for | What it costs on Claude |
|---|---|---|
| **Explore** (once) | Genuinely novel problem: figure out the right approach, the edge cases, the failure modes. Open-ended, needs judgment. | Run it at the model/effort tier the *hardest* part of the problem needs — Claude Opus 5 at `high` or `xhigh` effort, or Claude Fable 5 for the genuinely hardest long-horizon design work. |
| **Codify** (every time after) | The approach is known. Execution just needs to follow it faithfully and flag when a case doesn't fit. | Run it at the model/effort tier *execution* needs — often Claude Sonnet 5 or Claude Haiku 4.5, frequently with `low`/`medium` effort. |

The workshop's whole cost story is this table. Everything downstream — the
governance plugin in Demo 2, the meter in Demo 3 — exists to make the second row
cheap and to prove, with real metered numbers, that it stayed cheap.

## Run it

```bash
# Install genesis (see https://github.com/danielmeppiel/genesis for current install steps)
genesis design --target claude-code
```

Point `genesis` at a task your team repeats — a changelog entry, a PR description
against a fixed template, a routine migration step — and let it run the exploration
phase once. `genesis` produces a codified workflow definition; the output is what
Demo 2's `cost-aware-loop` skill (`../demo2-govern/skills/cost-aware-loop/SKILL.md`)
is a worked example of: fixed steps, explicit "this doesn't fit, escalate" language,
and no expectation that the cheap tier ever needs to think as hard as exploration
did.

## Why this matters more on Claude than it sounds

Claude Code has no separate "explore" and "execute" product surfaces — it's one
tool, and the discipline is entirely about *which model and effort level you choose
for which phase of the work*, deliberately, rather than defaulting to the most
capable (and most expensive) setting for everything because it's the path of least
resistance. Demo 3's meter (`../demo3-meter/`) is what proves, after the fact,
whether that discipline actually held — see its dashboard's per-model cost
breakdown for the gap between a workflow that respected this split and one that
didn't.

## Credits

`genesis` — [danielmeppiel/genesis](https://github.com/danielmeppiel/genesis).
Demo adapted from `danielmeppiel/finops-workshop`'s Demo 1.
