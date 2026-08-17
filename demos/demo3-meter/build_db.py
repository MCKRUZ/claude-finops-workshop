"""build_db.py — scans your local Claude Code session logs and builds
finops.db. Stdlib only, no dependencies, no network access.

Usage:
    python3 build_db.py
    CLAUDE_PROJECTS_DIR=/custom/path python3 build_db.py   # override

Reads only ~/.claude/projects (or CLAUDE_PROJECTS_DIR). Nothing leaves your
machine. finops.db is gitignored — it contains your real usage.

See VALIDATION.md for what's measured vs. modeled vs. best-effort-labeled
in the tables this script writes, and README.md for the "these are
API-equivalent dollars, not your bill" caveat that applies to every $ figure
below.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import finops_core as fc

DB_PATH = Path(__file__).parent / "finops.db"

SCHEMA = """
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    project_path TEXT,
    start_time TEXT,
    end_time TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    usd REAL DEFAULT 0.0,                 -- MEASURED: sum of every priced message in this session
    unpriced_message_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0
);

-- MEASURED per-model totals for a session.
CREATE TABLE session_models (
    session_id TEXT,
    model TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    usd REAL DEFAULT 0.0,
    message_count INTEGER DEFAULT 0,
    PRIMARY KEY (session_id, model)
);

-- MEASURED subagent (Task-tool) delegation cost — each subagent's own log
-- entries are summed directly, no estimation. subagent_type is a
-- best-effort LABEL only (nearest-preceding Task call by timestamp);
-- label_confidence flags when that label could not be recovered.
CREATE TABLE session_subagents (
    session_id TEXT,
    agent_id TEXT,
    subagent_type TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    usd REAL DEFAULT 0.0,
    label_confidence TEXT DEFAULT 'unlabeled',   -- 'matched' | 'unlabeled'
    PRIMARY KEY (session_id, agent_id)
);

-- MODELED main-thread cost, attributed at user-turn granularity. Every
-- main-thread assistant turn between human message N and N+1 is charged to
-- whichever skill(s) that turn invoked (skill_name is NULL for turns with
-- no skill invocation). shared=1 marks a turn that invoked more than one
-- skill, so its cost is split, not double-counted.
CREATE TABLE session_skill_turns (
    session_id TEXT,
    turn_index INTEGER,
    skill_name TEXT,
    usd REAL DEFAULT 0.0,
    shared INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0
);

-- MEASURED invocation counts only (no dollar attribution — these are
-- point operations, same "honest limitation" as the original Copilot
-- meter's tool-ranking table).
CREATE TABLE session_tools (
    session_id TEXT,
    kind TEXT,             -- 'tool' | 'skill' | 'subagent'
    tool_name TEXT,
    invocation_count INTEGER DEFAULT 0,
    PRIMARY KEY (session_id, kind, tool_name)
);

CREATE TABLE etl_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def projects_root() -> Path:
    override = os.environ.get("CLAUDE_PROJECTS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".claude" / "projects"


def find_jsonl_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.jsonl"))


def is_subagent_file(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return "subagents" in rel.parts


def load_agent_type_labels(files: list[Path], root: Path) -> dict[str, str]:
    """Map agent_id -> subagent type, read from the `<agent-id>.meta.json`
    sidecar Claude Code writes next to each subagent transcript
    (`subagents/agent-<id>.jsonl` + `subagents/agent-<id>.meta.json`).
    Covers ~100% of subagent files on a real install — this is the primary,
    exact labeling source; build()'s timestamp-based fallback only kicks in
    for the rare file missing one (or an older Claude Code version that
    never wrote sidecars at all)."""
    import json as _json

    labels: dict[str, str] = {}
    for path in files:
        if not is_subagent_file(path, root):
            continue
        if not path.name.startswith("agent-") or not path.name.endswith(".jsonl"):
            continue
        agent_id = path.name[len("agent-"):-len(".jsonl")]
        meta_path = path.parent / f"agent-{agent_id}.meta.json"
        if not meta_path.exists():
            continue
        try:
            meta = _json.loads(meta_path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError):
            continue
        label = meta.get("agentType") or meta.get("subagent_type") or meta.get("type")
        if label:
            labels[agent_id] = label
    return labels


def project_path_for(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return str(path.parent)
    return rel.parts[0] if rel.parts else str(path.parent)


def load_billable_entries(files: list[Path], root: Path) -> tuple[list[dict], dict[str, int]]:
    """Read every file, parse every line, keep only billable assistant
    entries, and dedupe globally on message id. Order of files/lines
    doesn't affect the result — whichever copy of a duplicated message is
    seen first wins, and their usage numbers are identical by construction
    (same underlying API response)."""
    seen_ids: set[str] = set()
    entries: list[dict] = []
    skipped_type_counts: dict[str, int] = {}

    for path in files:
        subagent_file = is_subagent_file(path, root)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            raw = fc.parse_jsonl_line(line)
            if raw is None:
                continue
            if not fc.is_billable_assistant_entry(raw):
                t = raw.get("type", "<no-type>") if isinstance(raw, dict) else "<non-dict>"
                skipped_type_counts[t] = skipped_type_counts.get(t, 0) + 1
                continue
            mid = fc.message_id(raw)
            if mid is None or mid in seen_ids:
                continue
            seen_ids.add(mid)
            raw["_source_path"] = str(path)
            raw["_is_subagent_file"] = subagent_file
            raw["_project_path"] = project_path_for(path, root)
            entries.append(raw)

    entries.sort(key=lambda e: e.get("timestamp") or "")
    return entries, skipped_type_counts


def build(db_path: Path = DB_PATH, root: Path | None = None) -> dict:
    root = root or projects_root()
    files = find_jsonl_files(root)
    entries, skipped_type_counts = load_billable_entries(files, root)
    agent_type_labels = load_agent_type_labels(files, root)

    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    sessions: dict[str, dict] = {}
    session_models: dict[tuple[str, str], dict] = {}
    session_tools: dict[tuple[str, str, str], int] = {}

    # For subagent labeling: session_id -> list of (timestamp, subagent_type)
    # Task calls seen on the MAIN thread, in order.
    task_calls: dict[str, list[tuple[str, str]]] = {}
    # session_id -> agent_id -> accumulated usage/cost
    subagents: dict[tuple[str, str], dict] = {}

    # For skill-turn attribution: session_id -> ordered list of
    # (turn_index, skill_names_invoked_this_turn)
    turn_index_by_session: dict[str, int] = {}
    skill_turns: dict[tuple[str, int, str], dict] = {}

    unpriced_models: set[str] = set()

    for entry in entries:
        session_id = entry.get("sessionId") or "unknown-session"
        is_sidechain = bool(entry.get("isSidechain"))
        is_subagent_file_entry = entry["_is_subagent_file"]
        message = entry["message"]
        model = message.get("model") or "unknown-model"
        usage = message.get("usage") or {}
        timestamp = entry.get("timestamp")
        cost = fc.compute_message_cost(model, usage, timestamp)
        if not cost.priced:
            unpriced_models.add(model)

        input_tokens = usage.get("input_tokens", 0) or 0
        output_tokens = usage.get("output_tokens", 0) or 0
        cache_read = usage.get("cache_read_input_tokens", 0) or 0
        cache_write = (usage.get("cache_creation_input_tokens", 0) or 0)

        s = sessions.setdefault(
            session_id,
            {
                "project_path": entry["_project_path"],
                "start_time": timestamp,
                "end_time": timestamp,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "usd": 0.0,
                "unpriced_message_count": 0,
                "message_count": 0,
            },
        )
        if timestamp:
            if not s["start_time"] or timestamp < s["start_time"]:
                s["start_time"] = timestamp
            if not s["end_time"] or timestamp > s["end_time"]:
                s["end_time"] = timestamp
        s["input_tokens"] += input_tokens
        s["output_tokens"] += output_tokens
        s["cache_read_tokens"] += cache_read
        s["cache_write_tokens"] += cache_write
        s["usd"] += cost.total_usd
        s["message_count"] += 1
        if not cost.priced:
            s["unpriced_message_count"] += 1

        mkey = (session_id, model)
        sm = session_models.setdefault(
            mkey,
            {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "usd": 0.0, "message_count": 0},
        )
        sm["input_tokens"] += input_tokens
        sm["output_tokens"] += output_tokens
        sm["cache_read_tokens"] += cache_read
        sm["cache_write_tokens"] += cache_write
        sm["usd"] += cost.total_usd
        sm["message_count"] += 1

        # Subagent content: anything written into a dedicated subagent file,
        # OR an inline isSidechain=true entry (installs that keep subagent
        # turns fully inline). Grouped by agentId when present; falls back
        # to "unknown" so its dollars are still counted somewhere.
        if is_subagent_file_entry or is_sidechain:
            agent_id = entry.get("agentId") or "unknown"
            akey = (session_id, agent_id)
            sub = subagents.setdefault(
                akey,
                {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "usd": 0.0},
            )
            sub["input_tokens"] += input_tokens
            sub["output_tokens"] += output_tokens
            sub["cache_read_tokens"] += cache_read
            sub["cache_write_tokens"] += cache_write
            sub["usd"] += cost.total_usd
            continue  # not part of the main thread — no turn/skill/tool attribution

        # Main-thread entry: attribute to the current turn, and record any
        # tool/skill/subagent invocations it made.
        for tool_use in fc.extract_tool_uses(entry):
            tkey = (session_id, tool_use["kind"], tool_use["name"])
            session_tools[tkey] = session_tools.get(tkey, 0) + 1
            if tool_use["kind"] == "subagent" and timestamp:
                task_calls.setdefault(session_id, []).append((timestamp, tool_use["name"]))

        turn_index = turn_index_by_session.get(session_id, 0)
        turn_index_by_session[session_id] = turn_index  # unchanged until next human turn

        skills_this_turn = [tu["name"] for tu in fc.extract_tool_uses(entry) if tu["kind"] == "skill"]
        skill_key_names = skills_this_turn or [None]
        shared = 1 if len(skills_this_turn) > 1 else 0
        for skill_name in skill_key_names:
            tkey2 = (session_id, turn_index, skill_name)
            st = skill_turns.setdefault(
                tkey2, {"usd": 0.0, "shared": shared, "input_tokens": 0, "output_tokens": 0}
            )
            # Split cost evenly across skills invoked in the same turn.
            share = cost.total_usd / len(skill_key_names)
            st["usd"] += share
            st["input_tokens"] += input_tokens // len(skill_key_names)
            st["output_tokens"] += output_tokens // len(skill_key_names)
            st["shared"] = shared

    # Second pass over raw entries just for turn-boundary detection (human
    # user turns) — done separately so the loop above stays flat.
    for entry in entries:
        if fc.is_human_user_turn(entry):
            sid = entry.get("sessionId") or "unknown-session"
            turn_index_by_session[sid] = turn_index_by_session.get(sid, 0) + 1

    # Label subagents. Primary source: the `agent-<id>.meta.json` sidecar
    # Claude Code writes next to each subagent transcript, which carries the
    # exact subagent type (covers ~100% of files on a real install — see
    # load_agent_type_labels). Fallback for the rare file with no sidecar
    # (or an older Claude Code version that never wrote one): nearest
    # unclaimed Task/Agent call in session order — a best-effort guess,
    # not a measurement, and flagged as such via label_confidence.
    subagent_rows = []
    for (session_id, agent_id), totals in subagents.items():
        label = agent_type_labels.get(agent_id)
        if label:
            confidence = "matched"
        else:
            calls = sorted(task_calls.get(session_id, []))
            if calls:
                label, confidence = calls[0][1], "matched (timestamp fallback)"
                task_calls[session_id] = calls[1:]
            else:
                label, confidence = "unknown-subagent", "unlabeled"
        subagent_rows.append(
            (session_id, agent_id, label, totals["input_tokens"], totals["output_tokens"],
             totals["cache_read_tokens"], totals["cache_write_tokens"], totals["usd"], confidence)
        )

    conn.executemany(
        "INSERT INTO sessions (session_id, project_path, start_time, end_time, input_tokens, "
        "output_tokens, cache_read_tokens, cache_write_tokens, total_tokens, usd, "
        "unpriced_message_count, message_count) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                sid, s["project_path"], s["start_time"], s["end_time"], s["input_tokens"],
                s["output_tokens"], s["cache_read_tokens"], s["cache_write_tokens"],
                s["input_tokens"] + s["output_tokens"] + s["cache_read_tokens"] + s["cache_write_tokens"],
                round(s["usd"], 6), s["unpriced_message_count"], s["message_count"],
            )
            for sid, s in sessions.items()
        ],
    )
    conn.executemany(
        "INSERT INTO session_models (session_id, model, input_tokens, output_tokens, "
        "cache_read_tokens, cache_write_tokens, usd, message_count) VALUES (?,?,?,?,?,?,?,?)",
        [
            (sid, model, sm["input_tokens"], sm["output_tokens"], sm["cache_read_tokens"],
             sm["cache_write_tokens"], round(sm["usd"], 6), sm["message_count"])
            for (sid, model), sm in session_models.items()
        ],
    )
    conn.executemany(
        "INSERT INTO session_subagents (session_id, agent_id, subagent_type, input_tokens, "
        "output_tokens, cache_read_tokens, cache_write_tokens, usd, label_confidence) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        subagent_rows,
    )
    conn.executemany(
        "INSERT INTO session_skill_turns (session_id, turn_index, skill_name, usd, shared, "
        "input_tokens, output_tokens) VALUES (?,?,?,?,?,?,?)",
        [
            (sid, turn_idx, skill, round(v["usd"], 6), v["shared"], v["input_tokens"], v["output_tokens"])
            for (sid, turn_idx, skill), v in skill_turns.items()
        ],
    )
    conn.executemany(
        "INSERT INTO session_tools (session_id, kind, tool_name, invocation_count) VALUES (?,?,?,?)",
        [(sid, kind, name, count) for (sid, kind, name), count in session_tools.items()],
    )

    meta = {
        "generated_note": "All usd figures are notional API-equivalent cost, not a subscription bill.",
        "files_scanned": str(len(files)),
        "billable_messages": str(len(entries)),
        "unpriced_models": ",".join(sorted(unpriced_models)) or "(none)",
        "skipped_entry_types": ",".join(f"{k}:{v}" for k, v in sorted(skipped_type_counts.items())),
    }
    conn.executemany("INSERT INTO etl_metadata (key, value) VALUES (?,?)", list(meta.items()))

    conn.commit()
    conn.close()
    return meta


if __name__ == "__main__":
    root = projects_root()
    if not root.exists():
        print(f"No Claude Code logs found at {root}", file=sys.stderr)
        print("Set CLAUDE_PROJECTS_DIR to override, or run some Claude Code sessions first.", file=sys.stderr)
        sys.exit(1)
    meta = build(root=root)
    print(f"Scanned {meta['files_scanned']} log files, {meta['billable_messages']} billable messages.")
    if meta["unpriced_models"] != "(none)":
        print(f"WARNING: no pricing data for: {meta['unpriced_models']} (tokens counted, $ omitted)")
    print(f"Wrote {DB_PATH}")
