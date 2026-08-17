"""compare_skill_cost.py — diffs OTel-measured skill cost (captured by
otel_bridge.py) against this meter's modeled skill-turn attribution (from
../dashboard_data.json), for the session(s) you ran with telemetry on.

Usage:
    python3 compare_skill_cost.py

Prints, per skill.name seen in the OTel capture: the real measured cost
(sum of claude_code.cost.usage data points tagged with that skill), the
modeled cost from the local-log meter for the same skill name across all
sessions, and the difference. A close match is evidence the turn-attribution
model in build_db.py is a reasonable approximation; a large gap is a signal
to revisit it — see VALIDATION.md.

Caveat: this compares GLOBAL modeled totals (across every session the local
meter has ever seen) against the OTel capture from whatever session(s) you
ran with telemetry on. For an apples-to-apples comparison, run this right
after a single fresh, isolated Claude Code session, before running anything
else that would add to the modeled totals.
"""

import json
from collections import defaultdict
from pathlib import Path

CAPTURE_PATH = Path(__file__).parent / "otel_capture.jsonl"
DASHBOARD_DATA_PATH = Path(__file__).parent.parent / "dashboard_data.json"


def load_otel_skill_costs(path: Path = CAPTURE_PATH) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    if not path.exists():
        return dict(totals)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        if record.get("metric") != "claude_code.cost.usage":
            continue
        skill = record.get("attributes", {}).get("skill.name")
        if not skill:
            continue
        totals[skill] += record.get("value", 0.0)
    return dict(totals)


def load_modeled_skill_costs(path: Path = DASHBOARD_DATA_PATH) -> dict[str, float]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["skill_name"]: row["usd"] for row in data.get("top_skills", [])}


def main() -> None:
    otel = load_otel_skill_costs()
    modeled = load_modeled_skill_costs()

    if not otel:
        print(f"No OTel skill-cost data found at {CAPTURE_PATH}.")
        print("Run otel_bridge.py, point a Claude Code session at it with telemetry")
        print("enabled, invoke a skill, then re-run this script.")
        return

    print(f"{'skill':<28} {'OTel (measured)':>18} {'meter (modeled)':>18} {'delta':>10}")
    for skill in sorted(set(otel) | set(modeled)):
        measured = otel.get(skill, 0.0)
        model = modeled.get(skill, 0.0)
        delta = model - measured
        print(f"{skill:<28} ${measured:>16.4f} ${model:>16.4f} ${delta:>8.4f}")

    print()
    print("A model consistently over- or under-shooting measured cost is a signal to")
    print("revisit the turn-attribution logic in build_db.py — see VALIDATION.md.")


if __name__ == "__main__":
    main()
