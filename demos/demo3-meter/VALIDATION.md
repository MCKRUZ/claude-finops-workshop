# Validation — what's measured, what's modeled, what's a best-effort label

This meter was built and tested against ~3,000 real local Claude Code log files on a
genuinely heavily-used development machine (415 sessions, ~83,000 billable messages,
~20 billion tokens). Read this before quoting any number it produces.

## The one thing that matters most

**Every dollar figure is a notional, API-equivalent cost** — what the token usage
would cost at Anthropic's published per-token API rates. It is **not** what you were
billed. Most Claude Code users are on a flat-rate subscription (Pro/Max/Team), not
pay-per-token billing. On the machine this was validated against, the meter reports
over $12,500 of API-equivalent usage from a subscription that costs a fixed monthly
fee — that gap is not a bug, it's the entire point of the disclaimer on every page of
the dashboard. Never present these numbers as "what this cost."

## MEASURED (trust as fact)

- **Per-session and per-model tokens/dollars.** Every assistant turn's real
  `usage` block (`input_tokens`, `output_tokens`, `cache_read_input_tokens`,
  `cache_creation_input_tokens`) is summed directly — this is the actual Anthropic
  API response embedded in your local logs, not an estimate.
- **Subagent (delegated-agent) cost.** Each subagent invocation writes its own
  separate log file with its own real `usage` entries — summing that file gives
  exact dollars for that piece of work. This is the direct improvement over the
  original GitHub Copilot version of this meter, whose logs carry no per-message
  cost at all and so could only *guess* skill/subagent cost from timing windows.
- **Subagent type labels**, for ~100% of invocations on every install checked
  during development: Claude Code writes a `<agent-id>.meta.json` sidecar next to
  each subagent transcript carrying the exact subagent type. (A timestamp-based
  fallback exists for the rare file missing one, or an older Claude Code version
  that never wrote sidecars — see `build_db.py`'s `load_agent_type_labels()`. Rows
  using the fallback are marked `matched (timestamp fallback)`, not `matched`.)
- **Tool/skill invocation counts.** How many times each tool or skill fired.

## MODELED (a reasoned estimate, not a measurement)

- **In-session skill cost.** A Skill invocation has no closing event and its
  instructions stay live in context for every turn after it loads — there is no
  clean signal for exactly which later tokens "belong" to it. This meter attributes
  cost at **user-turn granularity**: every assistant turn between one human message
  and the next is charged to whichever skill(s) that turn invoked (split evenly
  across skills when a turn invokes more than one). This is a narrower, more
  defensible version of the same limitation the original Copilot meter had for
  *all* skill cost — here it only applies to skills used inline in the main
  conversation thread, not to delegated subagent work (which is measured, above).

## NOT DERIVABLE

- **Truthful per-tool dollars.** Ordinary tool calls (Read, Edit, Bash, etc.) are
  point operations with no token span of their own — they're ranked by invocation
  count only, same honest limitation as the original meter.

## Sanity checks run during development

- **`sessions.usd == SUM(session_subagents.usd) + SUM(session_skill_turns.usd)`**
  for every real session tested — the measured session total always exactly
  decomposes into its measured subagent portion plus its modeled main-thread
  portion, with no double-counting and nothing dropped.
- **Dedup correctness**: verified against a session containing both an inline
  `isSidechain: true` copy of a subagent turn and that subagent's own separate log
  file — the global dedup on the Anthropic message id (`message.id`) correctly
  counted it once, not twice.
- **Unknown-model handling**: a synthetic/internal model id present in real logs
  was correctly left unpriced (`usd = null`, surfaced in `etl_metadata` and the
  dashboard) rather than silently guessed at a price.
- **Cache pricing**: verified the 1-hour cache-write tier (2× input price) is read
  from the `cache_creation.ephemeral_1h_input_tokens` breakdown when present, and
  is never confused with the 5-minute default tier (1.25× input price) — these are
  not interchangeable and mixing them up materially over- or under-states cost on
  any session using long-TTL caching.

## Known limitations to disclose when presenting

- The pricing table is dated (`finops_core.py` → `PRICING_RULES`) and Sonnet 5's
  introductory pricing expires 2026-08-31 — regenerate/re-check before presenting
  after that date, or historical sessions from before the cutoff will silently be
  priced at the standard (higher) rate if the table isn't kept current.
- Legacy/older models not in the pricing table are counted in tokens but excluded
  from dollar totals — a workshop audience with a long Claude Code history may see
  a nonzero "unpriced messages" count. This is intentional (never guess a price),
  but explain it live so it doesn't read as a bug.
- Subagent type labeling depends on Claude Code writing the `.meta.json` sidecar
  file next to each subagent transcript. This was true for ~100% of subagent
  invocations across every install this was tested against, but is an
  implementation detail of Claude Code's local storage format, not a documented,
  stable public API — a future Claude Code release could change it. The fallback
  path exists specifically so labeling degrades gracefully (to a lower-confidence
  guess) rather than breaking outright if that happens.
