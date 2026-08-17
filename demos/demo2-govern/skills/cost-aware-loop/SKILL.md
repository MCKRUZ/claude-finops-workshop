---
name: cost-aware-loop
description: A pinned, reusable checklist for turning a repeated engineering task into a cheap loop — explore once at high effort, then codify the result into fixed steps a cheaper model can execute every time after. This is the workshop's Demo 2 (GOVERN) exhibit — the pinned, versioned workflow governed by this plugin's spend-gate hook, not a general-purpose skill meant for wide reuse outside the workshop.
---

# Cost-aware loop

This skill is what Demo 1 (DESIGN) produces and Demo 2 (GOVERN) pins and gates: a
codified, cheap, repeatable version of a task that was expensive to explore the
first time.

**The pattern, in one sentence:** spend once at the model/effort level the problem
actually needs to *discover* the right approach; spend every time after at the
model/effort level the *execution* of that already-known approach needs — which is
almost always lower.

## When to use this skill

Use it as a template for any task your team runs more than a handful of times with
the same shape — a changelog entry, a PR description against a fixed template, a
weekly status rollup, a routine code-migration step. Don't use it for genuinely
novel, one-off work; that's what the expensive exploration phase (Demo 1) is for.

## The steps (fixed — this is the point)

1. **Confirm the task matches the pattern this loop was designed for.** If the input
   looks meaningfully different from what the original exploration covered, stop and
   flag it — don't silently stretch a cheap loop to cover a case it wasn't designed
   for. That's a Demo-1 job, not this skill's.
2. **Follow the fixed procedure below** (fill this section in with your team's own
   codified steps — this is a template; the workshop's point is the *pattern*, not
   this specific example's content).
3. **Run the cheap model/effort tier.** This loop should not need frontier-tier
   reasoning — if it does, that's a signal the exploration phase didn't fully codify
   the approach, and it's worth another Demo-1 pass rather than continuing to pay
   frontier prices for a "repeatable" loop.
4. **Report what changed, plainly.** No exploratory narration — the exploration
   already happened, once, in Demo 1.

## Why this is pinned and gated

This skill ships inside a versioned plugin (`plugin.json` → `version`), so a change
to the loop is a deliberate new version, not a silent drift — the original
workshop's governance point, expressed with a native Claude Code mechanism instead
of a package manifest+lockfile. It's also wrapped by this plugin's
`hooks/budget-gate.py`, a `PreToolUse` hook that blocks this specific skill (and
only this skill) once the day's measured API-equivalent spend — read live from Demo
3's local meter — exceeds a configured cap. A cheap loop that's cheap in theory but
run thousands of times is still a real cost; the gate is what makes "governed" more
than a word on a slide.
