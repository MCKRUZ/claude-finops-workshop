"""finops_core.py — pricing math and log-parsing primitives for the Claude
Code FinOps meter.

Stdlib only, no dependencies. This module is deliberately side-effect-free
(no filesystem or network access) so it can be unit-tested against synthetic
fixtures — see test_finops_core.py.

IMPORTANT — read before quoting any number this module produces:
Every dollar figure here is a *notional, API-equivalent* cost: what the same
token usage would cost at Anthropic's published per-token API rates. Most
Claude Code users are on a flat-rate subscription (Pro/Max/Team), not
pay-per-token billing — this is NOT what you were charged. Always label
figures "API-equivalent cost", never "your bill". See README.md.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------

# Each rule: (model_id_prefix, input_usd_per_mtok, output_usd_per_mtok,
#             effective_from_iso, effective_until_iso)
# `from`/`until` are ISO-8601 UTC strings, or None for open-ended.
#
# Matching: candidate rules are every rule whose prefix the model id starts
# with, preferring the LONGEST prefix (so "claude-opus-4-8" beats
# "claude-opus-4" ), then filtered to the rule whose [from, until) window
# contains the message timestamp. A model id this table doesn't recognize at
# all returns no price — this code never guesses a rate.
#
# Prices confirmed current as of 2026-08-17 (see demo3-meter/README.md for
# how to refresh this table as pricing changes).
PricingRule = tuple  # (prefix, input_price, output_price, from_iso, until_iso)

PRICING_RULES: list[PricingRule] = [
    ("claude-fable-5", 10.00, 50.00, None, None),
    ("claude-mythos-5", 10.00, 50.00, None, None),
    ("claude-opus-5", 5.00, 25.00, None, None),
    ("claude-opus-4-8", 5.00, 25.00, None, None),
    ("claude-opus-4-7", 5.00, 25.00, None, None),
    ("claude-opus-4-6", 5.00, 25.00, None, None),
    # Sonnet 5 carries time-boxed introductory pricing. The time-boxed rule
    # is listed first (matching logic doesn't care about list order — the
    # timestamp window disambiguates — but reading top-to-bottom, this is
    # "special rate while it lasts, standard rate after").
    ("claude-sonnet-5", 2.00, 10.00, None, "2026-08-31T23:59:59Z"),
    ("claude-sonnet-5", 3.00, 15.00, "2026-08-31T23:59:59Z", None),
    ("claude-sonnet-4-6", 3.00, 15.00, None, None),
    ("claude-haiku-4-5", 1.00, 5.00, None, None),
]

# Cache tokens are priced relative to that model's *input* rate.
CACHE_READ_MULTIPLIER = 0.10
CACHE_WRITE_5M_MULTIPLIER = 1.25  # default TTL
CACHE_WRITE_1H_MULTIPLIER = 2.00  # only when the log tells us it was 1h


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def price_for_model(model_id: str, timestamp: Optional[str]) -> Optional[tuple[float, float]]:
    """Return (input_usd_per_mtok, output_usd_per_mtok) for model_id as of
    timestamp, or None if this table has no price for it.

    Matching is by prefix because logs carry dated/versioned ids (e.g.
    "claude-sonnet-4-5-20250929"), not the bare aliases in PRICING_RULES.
    """
    if not model_id:
        return None
    ts = _parse_ts(timestamp)
    candidates = [r for r in PRICING_RULES if model_id.startswith(r[0])]
    if not candidates:
        return None
    candidates = sorted(candidates, key=lambda r: len(r[0]), reverse=True)
    for _prefix, in_price, out_price, eff_from, eff_until in candidates:
        f, u = _parse_ts(eff_from), _parse_ts(eff_until)
        if ts is not None:
            if f is not None and ts < f:
                continue
            if u is not None and ts >= u:
                continue
        return (in_price, out_price)
    return None


@dataclass
class MessageCost:
    priced: bool
    input_usd: float = 0.0
    output_usd: float = 0.0
    cache_read_usd: float = 0.0
    cache_write_usd: float = 0.0

    @property
    def total_usd(self) -> float:
        return self.input_usd + self.output_usd + self.cache_read_usd + self.cache_write_usd


def compute_message_cost(model_id: str, usage: dict, timestamp: Optional[str] = None) -> MessageCost:
    """API-equivalent USD cost for one assistant message's `usage` block.

    Returns priced=False (all-zero) when the model has no known price —
    callers MUST surface that rather than silently omitting it, so unknown
    models show up as "token counts, no $" instead of vanishing.
    """
    rates = price_for_model(model_id, timestamp)
    if rates is None:
        return MessageCost(priced=False)
    in_price, out_price = rates

    input_tokens = usage.get("input_tokens", 0) or 0
    output_tokens = usage.get("output_tokens", 0) or 0
    cache_read_tokens = usage.get("cache_read_input_tokens", 0) or 0

    # Cache-write tokens are priced differently by TTL (1.25x vs 2x input).
    # Prefer the detailed breakdown when the log carries it; otherwise treat
    # any flat cache_creation_input_tokens as the 5-minute default rather
    # than guessing at the more expensive 1-hour tier.
    cache_creation = usage.get("cache_creation") or {}
    if cache_creation:
        cache_5m = cache_creation.get("ephemeral_5m_input_tokens", 0) or 0
        cache_1h = cache_creation.get("ephemeral_1h_input_tokens", 0) or 0
    else:
        cache_5m = usage.get("cache_creation_input_tokens", 0) or 0
        cache_1h = 0

    return MessageCost(
        priced=True,
        input_usd=input_tokens / 1_000_000 * in_price,
        output_usd=output_tokens / 1_000_000 * out_price,
        cache_read_usd=cache_read_tokens / 1_000_000 * in_price * CACHE_READ_MULTIPLIER,
        cache_write_usd=(
            cache_5m / 1_000_000 * in_price * CACHE_WRITE_5M_MULTIPLIER
            + cache_1h / 1_000_000 * in_price * CACHE_WRITE_1H_MULTIPLIER
        ),
    )


# ---------------------------------------------------------------------------
# Log-entry parsing primitives
# ---------------------------------------------------------------------------
#
# Claude Code's local session log is JSONL: one JSON object per line, each
# carrying a top-level "type" that's either a real conversation turn
# ("assistant" / "user") or one of a growing family of harness-internal
# envelope types (hook results, tool listings, reminders, etc.) that this
# module deliberately ignores rather than trying to enumerate exhaustively —
# different installs and versions carry different sets of these, and a
# parser that asserts a fixed enum will break on the next Claude Code
# release. Only entries that match the shapes below are ever billed.


def parse_jsonl_line(line: str) -> Optional[dict]:
    """Safe JSON parse of one JSONL line. A blank or malformed line (real
    files can have partial trailing writes) returns None instead of
    raising."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def is_billable_assistant_entry(entry: object) -> bool:
    """True if this entry is a real Claude turn carrying billable usage."""
    if not isinstance(entry, dict) or entry.get("type") != "assistant":
        return False
    message = entry.get("message")
    if not isinstance(message, dict) or message.get("role") != "assistant":
        return False
    return isinstance(message.get("usage"), dict)


def message_id(entry: dict) -> Optional[str]:
    """The underlying Anthropic API response id — the dedup key. The same
    message can legitimately appear more than once in the logs (a subagent
    turn written both inline with isSidechain=true AND in its own
    subagents/agent-<id>.jsonl file; a --resume/--continue session replaying
    prior turns) — callers must dedupe on this before summing anything."""
    if not is_billable_assistant_entry(entry):
        return None
    return entry["message"].get("id")


# Subagent-spawning tool's name varies by install: vanilla Claude Code uses
# "Task"; some harnesses (confirmed on a real machine during development)
# rename it "Agent". Both are recognized. If a future install uses another
# name, its calls fall through to kind="tool" (still counted, just not
# broken out as subagent delegation) rather than being silently dropped.
_SUBAGENT_TOOL_NAMES = {"Task", "Agent"}


def extract_tool_uses(entry: dict) -> list[dict]:
    """tool_use content blocks from a billable assistant entry, normalized:
    - Skill invocations (tool name "Skill") surface as {"kind": "skill",
      "name": <skill id>}
    - Subagent delegation (tool name "Task" or "Agent") surfaces as
      {"kind": "subagent", "name": <subagent_type>}
    - Everything else surfaces as {"kind": "tool", "name": <tool name>}
    """
    if not is_billable_assistant_entry(entry):
        return []
    out = []
    for block in entry["message"].get("content") or []:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = block.get("name")
        tool_input = block.get("input") or {}
        if name == "Skill":
            out.append({"kind": "skill", "name": tool_input.get("skill") or "unknown-skill"})
        elif name in _SUBAGENT_TOOL_NAMES:
            out.append({"kind": "subagent", "name": tool_input.get("subagent_type") or "unknown-subagent"})
        else:
            out.append({"kind": "tool", "name": name or "unknown-tool"})
    return out


def is_human_user_turn(entry: dict) -> bool:
    """True for a real human message — the boundary a new "turn" starts at
    for skill-attribution purposes. False for a synthetic 'user'-role entry
    that's actually a tool_result being fed back to the model, and false for
    subagent sidechain entries (they don't have human turns of their own)."""
    if not isinstance(entry, dict) or entry.get("type") != "user":
        return False
    if entry.get("isSidechain"):
        return False
    message = entry.get("message")
    if not isinstance(message, dict) or message.get("role") != "user":
        return False
    content = message.get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(isinstance(b, dict) and b.get("type") == "text" for b in content)
    return False
