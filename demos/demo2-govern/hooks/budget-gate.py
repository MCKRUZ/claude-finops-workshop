#!/usr/bin/env python3
"""budget-gate.py — a PreToolUse hook that blocks the governed
cost-aware-loop skill once today's API-equivalent spend (measured by Demo
3's local meter) exceeds a configured daily cap.

This is the "gated by policy" half of Demo 2 (GOVERN): the skill in this
plugin is the pinned, reusable workflow; this hook is the policy gate around
it, implemented on a native Claude Code primitive (hooks) rather than
anything apm-shaped.

Wired via hooks/hooks.json to fire on PreToolUse, matcher "Skill" — it only
acts when the invoked skill is this plugin's own cost-aware-loop; every
other skill call passes through untouched (exit 0, no decision).

Configuration:
    FINOPS_DAILY_CAP_USD   default 25.00 — the daily API-equivalent cap.
    FINOPS_DB_PATH         explicit override for finops.db's location.
                            Needed for a real plugin install: Claude Code
                            copies an installed plugin to a cache directory,
                            so a path relative to this script can't reliably
                            reach Demo 3's finops.db (a sibling directory in
                            the source repo) after that copy happens. Set
                            this env var, or run the workshop uninstalled
                            (straight from a repo checkout / local
                            marketplace add) where the relative fallback
                            below still works. See demo2-govern/README.md.

No finops.db found (any path) → allow, with an informational note. No data
means no evidence of overspend — a missing measurement is not a policy
violation.
"""

import json
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

GOVERNED_SKILL = "cost-aware-loop"
DEFAULT_CAP_USD = 25.00


def candidate_db_paths() -> list[Path]:
    candidates = []
    override = os.environ.get("FINOPS_DB_PATH")
    if override:
        candidates.append(Path(override))

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        # Uninstalled / local-source layout: <repo>/demos/demo2-govern (this
        # plugin) and <repo>/demos/demo3-meter are siblings under demos/.
        candidates.append(Path(plugin_root) / ".." / "demo3-meter" / "finops.db")

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        candidates.append(Path(project_dir) / "demos" / "demo3-meter" / "finops.db")

    return candidates


def todays_spend_usd(db_path: Path) -> float:
    conn = sqlite3.connect(db_path)
    try:
        today = date.today().isoformat()
        row = conn.execute(
            "SELECT ROUND(SUM(usd), 4) FROM sessions WHERE substr(start_time, 1, 10) = ?",
            (today,),
        ).fetchone()
        return row[0] or 0.0
    finally:
        conn.close()


def allow(reason: str | None = None) -> None:
    if reason:
        print(f"[budget-gate] {reason}", file=sys.stderr)
    sys.exit(0)


def deny(spend: float, cap: float) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"FinOps budget gate: today's API-equivalent spend (${spend:.2f}) "
                f"exceeds the configured daily cap (${cap:.2f}). This is a notional "
                f"cost figure, not a bill — see demos/demo3-meter/README.md. Raise "
                f"FINOPS_DAILY_CAP_USD or investigate before continuing."
            ),
        }
    }
    print(json.dumps(output))
    sys.exit(2)


def main() -> None:
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        allow("could not parse hook input, passing through")
        return

    if hook_input.get("tool_name") != "Skill":
        allow()
        return
    tool_input = hook_input.get("tool_input") or {}
    if tool_input.get("skill") != GOVERNED_SKILL:
        allow()
        return

    cap = float(os.environ.get("FINOPS_DAILY_CAP_USD", DEFAULT_CAP_USD))

    db_path = next((p for p in candidate_db_paths() if p.exists()), None)
    if db_path is None:
        allow(
            "no finops.db found (run demos/demo3-meter/build_db.py, or set "
            "FINOPS_DB_PATH) — allowing, since there's no data to enforce a cap against"
        )
        return

    try:
        spend = todays_spend_usd(db_path)
    except sqlite3.Error as e:
        allow(f"could not read {db_path}: {e} — allowing")
        return

    if spend > cap:
        deny(spend, cap)
    else:
        allow(f"today's spend ${spend:.2f} is within the ${cap:.2f} cap")


if __name__ == "__main__":
    main()
