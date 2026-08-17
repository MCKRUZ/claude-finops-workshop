# Demo 2 — GOVERN a reusable, cost-aware workflow

A Claude Code plugin demonstrating the workshop's second play: a workflow you
designed once (Demo 1) should be **pinned** (versioned, not silently drifting) and
**gated by policy** (blocked when it's actually costing too much), not just reused.

The original GitHub Copilot version of this demo used `apm` (Agent Package Manager)
for pinning and distribution. This port uses Claude Code's own plugin system
instead — `apm` claims Claude Code support, but has an open, reproducible bug in
that exact install path (`apm install --target claude` failing to deploy local
primitives) as of this writing. Claude Code's native mechanism does the same job
without that dependency: a plugin's `version` field pins the workflow, and a hook —
a genuinely native Claude Code primitive, not a Copilot-shaped workaround — gates
it.

## What's in this plugin

- **`skills/cost-aware-loop/SKILL.md`** — the pinned, reusable workflow: explore
  once at high effort/cost to find the right approach, then codify it into fixed
  steps a cheaper model runs every time after. This is a template; fill in your own
  team's codified steps.
- **`hooks/budget-gate.py`** (wired via `hooks/hooks.json`) — a `PreToolUse` hook
  that blocks the `cost-aware-loop` skill specifically once today's measured
  API-equivalent spend (read live from **Demo 3's** local `finops.db`) exceeds a
  configured daily cap. Every other tool/skill call passes through untouched.

## Install locally

From the repo root:

```bash
/plugin marketplace add .
/plugin install finops-govern@claude-finops-workshop
/reload-plugins   # if the install summary asks for it
```

Try the governed skill:

```
/finops-govern:cost-aware-loop
```

## Try the gate

The gate needs Demo 3's meter to have real data to check against:

```bash
cd ../demo3-meter && python3 build_db.py && cd ../demo2-govern
```

Then, to see it actually block: lower the cap below today's measured spend and
invoke the skill again.

```bash
export FINOPS_DAILY_CAP_USD=0.01
```

Restore the default (or unset the variable) to remove the artificial cap.

## Known limitation — cross-plugin file access

`budget-gate.py` reads `../demo3-meter/finops.db`, a sibling directory's output —
this works when running the workshop directly from a repo checkout or a local
marketplace add. **It will not work after a real `/plugin install`** from a remote
marketplace: Claude Code copies an installed plugin to a cache location, and a
copied plugin can't reach files outside its own directory. For a production
version of this pattern, set `FINOPS_DB_PATH` explicitly (see `budget-gate.py`'s
docstring) rather than relying on the relative-path fallback. This is disclosed,
not hidden, because a governance demo that silently no-ops after "real" install
would be worse than the thing it's replacing.

## Credits

Ported from `danielmeppiel/finops-workshop`'s Demo 2 (GitHub Copilot + `apm`).
