# Deck mockups — one ASCII sketch per slide

Design intent behind each built slide in `../docs/slides/`. Minimalist: one idea,
generous whitespace, a single accent color, no decoration that isn't information.

## cover.html

```
┌──────────────────────────────────────────────┐
│                                                │
│                                                │
│        FinOps for Agentic Coding              │
│        — Claude Code —                        │
│                                                │
│   Your agentic bill is a variance you          │
│   ENGINEER, not a price you negotiate.         │
│                                                │
│                                                │
│                                    [F to start]│
└──────────────────────────────────────────────┘
```

## intro.html

```
┌──────────────────────────────────────────────┐
│  This is for:              This is NOT:       │
│                                                │
│  · AI Champions            · Prompting 101    │
│  · Platform leads          · Model comparisons │
│  · Admins                  · A sales pitch     │
│                                                │
│  ~60 minutes. 3 live demos, run on real logs. │
└──────────────────────────────────────────────┘
```

## s01-number.html

```
┌──────────────────────────────────────────────┐
│                                                │
│              [ BIG NUMBER ]                   │
│         one team's illustrative gap            │
│      between a right-sized loop and a          │
│         re-explore-every-time habit             │
│                                                │
│   (we'll show you how to get YOUR number       │
│    — live, in Demo 3, in about 12 minutes)      │
└──────────────────────────────────────────────┘
```

## s02-reframe.html

```
┌──────────────────────────────────────────────┐
│   A line item you negotiate            ✗       │
│                                                │
│   A variance you engineer               ✓       │
│                                                │
│   The lever isn't the vendor contract.         │
│   It's the loop your agents run.               │
└──────────────────────────────────────────────┘
```

## s03-why-not-dev.html

```
┌──────────────────────────────────────────────┐
│   "Just write better prompts" doesn't scale.  │
│                                                │
│   This is an OPERATING MODEL problem:          │
│   who designs the loop, who governs it,        │
│   who's accountable for what it costs.         │
│                                                │
│              → DEMO 1: DESIGN                 │
└──────────────────────────────────────────────┘
```

## s04-demo-design.html

```
┌──────────────────────────────────────────────┐
│   EXPLORE (once)         CODIFY (every time)  │
│   ─────────────          ──────────────────   │
│   Opus 5 / Fable 5   →   Sonnet 5 / Haiku 4.5 │
│   open-ended              fixed steps          │
│   judgment                execution            │
│                                                │
│   genesis --target claude-code                │
└──────────────────────────────────────────────┘
```

## s05-lifecycle-loop.html

```
┌──────────────────────────────────────────────┐
│        ┌─────────┐                            │
│   ┌───▶│ DESIGN  │───┐                        │
│   │    └─────────┘   ▼                        │
│   │              ┌─────────┐                  │
│   │              │ GOVERN  │                  │
│   │              └─────────┘                  │
│   │                   │                        │
│   │                   ▼                        │
│   │              ┌─────────┐                  │
│   └──────────────│ MEASURE │                  │
│      feeds back  └─────────┘                  │
└──────────────────────────────────────────────┘
```

## s06-money.html

```
┌──────────────────────────────────────────────┐
│  ⚠ API-equivalent cost, not your bill          │
│                                                │
│  Right-sized loop         [regenerate locally]│
│  Same model, bad loop     [regenerate locally]│
│  Premium everywhere       [regenerate locally]│
│                                                │
│  Run demos/demo3-meter/ against YOUR logs      │
│  before you present this slide.                │
└──────────────────────────────────────────────┘
```

## s07-tooling.html

```
┌──────────────────────────────────────────────┐
│   Claude Code            the harness           │
│   Plugins + hooks        governance             │
│   genesis                design                │
│                                                │
│              → DEMO 2: GOVERN                 │
└──────────────────────────────────────────────┘
```

## s08-demo-govern.html

```
┌──────────────────────────────────────────────┐
│   skill: cost-aware-loop      [v1.0.0, pinned]│
│                                                │
│   hook: budget-gate.py                        │
│     PreToolUse → Skill → check spend → allow/  │
│     deny (exit 2)                              │
│                                                │
│   /plugin install finops-govern@...           │
└──────────────────────────────────────────────┘
```

## s09-demo-measure.html

```
┌──────────────────────────────────────────────┐
│   MEASURED          │  MODELED                │
│   ────────          │  ───────                │
│   session $          │  in-session skill $     │
│   subagent $ (exact) │  (turn-attributed)      │
│                                                │
│   $ python3 build_db.py && export_dashboard.py│
│   $ open dashboard.html      [live, your logs]│
└──────────────────────────────────────────────┘
```

## s10-playbook.html

```
┌──────────────────────────────────────────────┐
│   1. Tier the models                          │
│      match model/effort to the actual job      │
│                                                │
│   2. Pool the spend                           │
│      one visible number, not N invisible ones  │
│                                                │
│   3. Codify the top loops                      │
│      Demo 1 → Demo 2, pinned and gated          │
└──────────────────────────────────────────────┘
```

## s11-exercise.html

```
┌──────────────────────────────────────────────┐
│   Pick one task your team repeats weekly.      │
│                                                │
│   1. What does "explore" look like for it?     │
│   2. What would "codify" fix in place?         │
│   3. What model/effort does each half need?    │
│                                                │
│              [10 minutes, pairs]              │
└──────────────────────────────────────────────┘
```

## resources.html

```
┌──────────────────────────────────────────────┐
│   This repo                                   │
│   genesis — github.com/danielmeppiel/genesis  │
│   Claude Code plugin docs — code.claude.com   │
│   Anthropic pricing — platform.claude.com     │
│                                                │
│                    Thank you.                 │
└──────────────────────────────────────────────┘
```
