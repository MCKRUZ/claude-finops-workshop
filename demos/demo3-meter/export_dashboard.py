"""export_dashboard.py — reads finops.db and emits dashboard_data.json plus a
self-contained dashboard.html. Stdlib only.

Usage:
    python3 build_db.py && python3 export_dashboard.py
    open dashboard.html   # (or: start dashboard.html on Windows)

dashboard.html embeds its data inline (no fetch(), no local server needed)
so it opens directly from the filesystem. dashboard_data.json is written
alongside it as a separate, reusable artifact — e.g. for the OTel cross-check
tool in advanced/.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "finops.db"
DATA_PATH = Path(__file__).parent / "dashboard_data.json"
HTML_PATH = Path(__file__).parent / "dashboard.html"


def build_dashboard_data(db_path: Path = DB_PATH) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    summary = conn.execute(
        "SELECT COUNT(*) AS session_count, ROUND(SUM(usd),2) AS usd, "
        "SUM(total_tokens) AS total_tokens, SUM(message_count) AS message_count, "
        "SUM(unpriced_message_count) AS unpriced_message_count FROM sessions"
    ).fetchone()

    per_model = [dict(r) for r in conn.execute(
        "SELECT model, SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens, "
        "SUM(cache_read_tokens) AS cache_read_tokens, SUM(cache_write_tokens) AS cache_write_tokens, "
        "ROUND(SUM(usd),4) AS usd, SUM(message_count) AS messages "
        "FROM session_models GROUP BY model ORDER BY usd DESC"
    )]

    top_sessions = [dict(r) for r in conn.execute(
        "SELECT session_id, project_path, start_time, ROUND(usd,4) AS usd, total_tokens, message_count "
        "FROM sessions ORDER BY usd DESC LIMIT 25"
    )]

    top_subagents = [dict(r) for r in conn.execute(
        "SELECT subagent_type, COUNT(*) AS invocations, ROUND(SUM(usd),4) AS usd, "
        "SUM(input_tokens+output_tokens+cache_read_tokens+cache_write_tokens) AS tokens, "
        "label_confidence FROM session_subagents "
        "GROUP BY subagent_type, label_confidence ORDER BY usd DESC LIMIT 25"
    )]

    top_skills = [dict(r) for r in conn.execute(
        "SELECT skill_name, COUNT(DISTINCT session_id || ':' || turn_index) AS invocations, "
        "ROUND(SUM(usd),4) AS usd FROM session_skill_turns "
        "WHERE skill_name IS NOT NULL GROUP BY skill_name ORDER BY usd DESC LIMIT 25"
    )]

    top_tools = [dict(r) for r in conn.execute(
        "SELECT tool_name, kind, SUM(invocation_count) AS invocations "
        "FROM session_tools GROUP BY tool_name, kind ORDER BY invocations DESC LIMIT 30"
    )]

    meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM etl_metadata")}

    conn.close()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cost_disclosure": (
            "Every $ figure below is a NOTIONAL, API-EQUIVALENT cost — what this token "
            "usage would cost at Anthropic's published per-token API rates. It is NOT "
            "your subscription bill. Most Claude Code users are on a flat-rate plan "
            "(Pro/Max/Team), not pay-per-token billing."
        ),
        "measured_vs_modeled": {
            "session_and_model_totals": "MEASURED — summed from real per-message usage.",
            "subagent_cost": "MEASURED — each subagent's own log carries real usage; label matched from a metadata sidecar for ~100% of invocations on a typical install.",
            "in_session_skill_cost": "MODELED — attributed at user-turn granularity (see VALIDATION.md), not a per-skill measurement.",
            "tool_invocation_counts": "MEASURED counts only — no dollar figure is attributed to individual tool calls.",
        },
        "summary": dict(summary),
        "per_model": per_model,
        "top_sessions": top_sessions,
        "top_subagents": top_subagents,
        "top_skills": top_skills,
        "top_tools": top_tools,
        "etl_metadata": meta,
    }


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Claude Code FinOps Dashboard</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 15px/1.5 -apple-system, Segoe UI, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem;
         background: light-dark(#fafafa, #16161a); color: light-dark(#1a1a1a, #eaeaea); }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  .disclosure { background: light-dark(#fff3cd, #3a3320); border: 1px solid light-dark(#e0c34a, #6b5d1f);
                border-radius: 8px; padding: 0.85rem 1rem; margin: 1rem 0 1.5rem; font-size: 0.9rem; }
  .summary { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }
  .card { background: light-dark(#fff, #1f1f24); border: 1px solid light-dark(#e2e2e2, #333); border-radius: 10px;
          padding: 1rem 1.25rem; flex: 1; min-width: 140px; }
  .card .value { font-size: 1.6rem; font-weight: 700; }
  .card .label { font-size: 0.8rem; opacity: 0.7; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 0.88rem; }
  th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid light-dark(#eee, #2a2a2e); }
  th { opacity: 0.7; font-weight: 600; cursor: pointer; }
  tr:hover td { background: light-dark(#f3f3f3, #26262b); }
  section h2 { font-size: 1.05rem; border-bottom: 2px solid light-dark(#222,#eee); padding-bottom: 0.3rem; }
  .badge { font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 4px; }
  .measured { background: light-dark(#d4edda, #1e3a24); color: light-dark(#155724, #7fd996); }
  .modeled { background: light-dark(#fff3cd, #3a3320); color: light-dark(#856404, #e0c34a); }
  .mono { font-family: ui-monospace, monospace; font-size: 0.82rem; }
  input#filter { padding: 0.4rem 0.6rem; width: 100%; box-sizing: border-box; margin-bottom: 1rem;
                 border-radius: 6px; border: 1px solid light-dark(#ccc,#444); }
</style>
</head>
<body>
<h1>Claude Code FinOps Dashboard</h1>
<div class="disclosure">
  ⚠️ <strong>Every $ figure on this page is a notional, API-equivalent cost</strong> — what this
  token usage would cost at Anthropic's published API rates. It is <strong>not your bill</strong>.
  Most Claude Code users are on a flat-rate subscription, not pay-per-token billing.
</div>

<div class="summary" id="summary-cards"></div>

<input id="filter" type="text" placeholder="Filter sessions by project path or session id…">

<section>
  <h2>Cost by model <span class="badge measured">MEASURED</span></h2>
  <table id="per-model"><thead><tr><th>Model</th><th>Input tok</th><th>Output tok</th>
    <th>Cache read</th><th>Cache write</th><th>Messages</th><th>USD</th></tr></thead><tbody></tbody></table>
</section>

<section>
  <h2>Top sessions <span class="badge measured">MEASURED</span></h2>
  <table id="top-sessions"><thead><tr><th>Session</th><th>Project</th><th>Started</th>
    <th>Messages</th><th>Tokens</th><th>USD</th></tr></thead><tbody></tbody></table>
</section>

<section>
  <h2>Subagent delegation <span class="badge measured">MEASURED</span></h2>
  <p style="font-size:0.85rem;opacity:0.75">Each subagent invocation carries its own real
  token usage — no estimation. This is the direct upgrade over the original Copilot meter,
  which could only <em>model</em> per-skill/subagent cost.</p>
  <table id="top-subagents"><thead><tr><th>Subagent type</th><th>Invocations</th>
    <th>Tokens</th><th>USD</th><th>Label</th></tr></thead><tbody></tbody></table>
</section>

<section>
  <h2>In-session skill cost <span class="badge modeled">MODELED</span></h2>
  <p style="font-size:0.85rem;opacity:0.75">Attributed at user-turn granularity — every
  assistant turn between one human message and the next is charged to whichever skill(s)
  it invoked. This is an estimate, not a measurement — see VALIDATION.md.</p>
  <table id="top-skills"><thead><tr><th>Skill</th><th>Turns</th><th>USD (modeled)</th></tr></thead><tbody></tbody></table>
</section>

<section>
  <h2>Tool usage <span class="badge measured">MEASURED (counts only)</span></h2>
  <table id="top-tools"><thead><tr><th>Tool</th><th>Kind</th><th>Invocations</th></tr></thead><tbody></tbody></table>
</section>

<footer style="opacity:0.6;font-size:0.8rem;margin:2rem 0">
  Generated <span id="generated-at"></span> · reads only your local ~/.claude/projects logs ·
  nothing leaves your machine.
</footer>

<script id="finops-data" type="application/json">__DASHBOARD_DATA_JSON__</script>
<script>
const data = JSON.parse(document.getElementById('finops-data').textContent);
const fmtUsd = n => '$' + (n ?? 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtNum = n => (n ?? 0).toLocaleString();

document.getElementById('generated-at').textContent = data.generated_at;

const cards = [
  ['Total sessions', fmtNum(data.summary.session_count)],
  ['Total USD (API-equiv.)', fmtUsd(data.summary.usd)],
  ['Total tokens', fmtNum(data.summary.total_tokens)],
  ['Unpriced messages', fmtNum(data.summary.unpriced_message_count)],
];
document.getElementById('summary-cards').innerHTML = cards.map(([label, value]) =>
  `<div class="card"><div class="value">${value}</div><div class="label">${label}</div></div>`).join('');

const tbody = sel => document.querySelector(sel + ' tbody');

tbody('#per-model').innerHTML = data.per_model.map(m => `<tr>
  <td class="mono">${m.model}</td><td>${fmtNum(m.input_tokens)}</td><td>${fmtNum(m.output_tokens)}</td>
  <td>${fmtNum(m.cache_read_tokens)}</td><td>${fmtNum(m.cache_write_tokens)}</td>
  <td>${fmtNum(m.messages)}</td><td>${fmtUsd(m.usd)}</td></tr>`).join('');

function renderSessions(rows) {
  tbody('#top-sessions').innerHTML = rows.map(s => `<tr>
    <td class="mono">${s.session_id.slice(0,8)}…</td><td class="mono">${s.project_path}</td>
    <td>${(s.start_time||'').slice(0,10)}</td><td>${fmtNum(s.message_count)}</td>
    <td>${fmtNum(s.total_tokens)}</td><td>${fmtUsd(s.usd)}</td></tr>`).join('');
}
renderSessions(data.top_sessions);

document.getElementById('filter').addEventListener('input', e => {
  const q = e.target.value.toLowerCase();
  renderSessions(data.top_sessions.filter(s =>
    s.project_path.toLowerCase().includes(q) || s.session_id.toLowerCase().includes(q)));
});

tbody('#top-subagents').innerHTML = data.top_subagents.map(s => `<tr>
  <td class="mono">${s.subagent_type}</td><td>${fmtNum(s.invocations)}</td>
  <td>${fmtNum(s.tokens)}</td><td>${fmtUsd(s.usd)}</td>
  <td><span class="badge ${s.label_confidence.startsWith('matched') ? 'measured' : 'modeled'}">${s.label_confidence}</span></td></tr>`).join('');

tbody('#top-skills').innerHTML = data.top_skills.map(s => `<tr>
  <td class="mono">${s.skill_name}</td><td>${fmtNum(s.invocations)}</td><td>${fmtUsd(s.usd)}</td></tr>`).join('');

tbody('#top-tools').innerHTML = data.top_tools.map(t => `<tr>
  <td class="mono">${t.tool_name}</td><td>${t.kind}</td><td>${fmtNum(t.invocations)}</td></tr>`).join('');
</script>
</body>
</html>
"""


def export(db_path: Path = DB_PATH, data_path: Path = DATA_PATH, html_path: Path = HTML_PATH) -> None:
    data = build_dashboard_data(db_path)
    data_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    # Escape "</" so a project path or session id containing "</script>"
    # can't break out of the embedded <script> block.
    embedded_json = json.dumps(data).replace("</", "<\\/")
    html = _HTML_TEMPLATE.replace("__DASHBOARD_DATA_JSON__", embedded_json)
    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote {data_path}")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit(f"{DB_PATH} not found — run build_db.py first.")
    export()
