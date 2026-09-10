#!/usr/bin/env python3
"""Renders a TraceOS model as a single self-contained HTML view.

The page is a VIEW over the model, never a source of truth: it is regenerated, not
edited. Every derived figure on it - effective reality, impact, coverage, integrity -
is computed by tools/traceos.py and embedded as a result. Nothing is recomputed in
JavaScript, so there is no second implementation to drift from the engine.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import pathlib

from . import engine as T

NODE_W, NODE_H, COL_GAP, ROW_GAP, PAD, CHIP_H = 168, 46, 96, 22, 26, 15

TYPE_COLOR = {
    "action": "var(--action)",
    "decision": "var(--decision)",
    "event": "var(--event)",
    "interaction": "var(--interaction)",
}
EDGE_STYLE = {
    "next": ("var(--edge)", ""),
    "invokes": ("var(--invokes)", "6 3"),
    "emits": ("var(--emits)", "2 3"),
    "triggers": ("var(--triggers)", "2 3"),
    "transitions_to": ("var(--state)", "1 4"),
    "interacts_with": ("var(--external)", "4 4"),
    "depends_on": ("var(--muted)", "1 4"),
}


def rank_nodes(node_ids: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    """Longest-path layering over `next`, so a branch renders to the right of what
    it branches from."""
    incoming = dict.fromkeys(node_ids, 0)
    for _, tgt in edges:
        if tgt in incoming:
            incoming[tgt] += 1
    rank = dict.fromkeys(node_ids, 0)
    for _ in range(len(node_ids)):
        changed = False
        for src, tgt in edges:
            if src in rank and tgt in rank and rank[tgt] < rank[src] + 1:
                rank[tgt] = rank[src] + 1
                changed = True
        if not changed:
            break
    return rank


def flow_svg(model: T.Model, fid: str) -> str:
    flow = model.flows[fid]
    nodes = [n["id"] for n in flow.get("nodes") or []]
    if not nodes:
        return '<p class="empty">no nodes declared</p>'
    rels = [r for r in model.relationships if r.get("_flow") == fid]
    next_edges = [(r["source"], r["target"]) for r in rels if r["type"] == "next"]

    rank = rank_nodes(nodes, next_edges)
    columns: dict[int, list[str]] = {}
    for node_id in nodes:
        columns.setdefault(rank[node_id], []).append(node_id)

    side: dict[str, list[tuple[str, str]]] = {}
    for rel in rels:
        if rel["type"] != "next":
            side.setdefault(rel["source"], []).append((rel["type"], rel["target"]))

    # Chips sit under their node, never to the right, or they collide with the
    # outgoing `next` arrow.
    pos: dict[str, tuple[float, float]] = {}
    height = PAD
    for col, members in sorted(columns.items()):
        y = PAD
        for node_id in members:
            pos[node_id] = (PAD + col * (NODE_W + COL_GAP), y)
            y += NODE_H + len(side.get(node_id, [])) * CHIP_H + ROW_GAP
        height = max(height, y)

    width = PAD * 2 + (max(rank.values()) + 1) * (NODE_W + COL_GAP)

    parts = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" '
        f'style="max-width:{width:.0f}px" role="img">'
    ]
    parts.append(
        "<defs>"
        '<marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7"'
        ' markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z"'
        ' fill="currentColor"/></marker></defs>'
    )

    seen_pairs: dict[tuple[str, str], int] = {}
    for rel in rels:
        if rel["type"] != "next":
            continue
        src, tgt = pos.get(rel["source"]), pos.get(rel["target"])
        if not src or not tgt:
            continue
        pair = (rel["source"], rel["target"])
        # Parallel edges between the same pair must bow apart, or their condition
        # labels land on top of each other.
        index = seen_pairs.get(pair, 0)
        seen_pairs[pair] = index + 1
        bow = (index - (index % 2) * 2) * 14
        # An edge that skips a column would otherwise pass behind the node in
        # between, so route it under.
        span = rank[rel["target"]] - rank[rel["source"]]
        if span > 1:
            bow += NODE_H + 18

        x1, y1 = src[0] + NODE_W, src[1] + NODE_H / 2
        x2, y2 = tgt[0], tgt[1] + NODE_H / 2
        mid = (x1 + x2) / 2
        color, _ = EDGE_STYLE["next"]
        parts.append(
            f'<path d="M{x1:.0f} {y1:.0f} C{mid:.0f} {y1 + bow:.0f} '
            f'{mid:.0f} {y2 + bow:.0f} {x2:.0f} {y2:.0f}" fill="none" '
            f'stroke="{color}" stroke-width="1.5" style="color:{color}" '
            f'marker-end="url(#a)"/>'
        )
        if rel.get("condition"):
            parts.append(
                f'<text class="cond" x="{mid:.0f}" '
                f'y="{(y1 + y2) / 2 + bow - 6:.0f}" text-anchor="middle">'
                f"{html.escape(rel['condition'])}</text>"
            )

    for node_id in nodes:
        x, y = pos[node_id]
        node = model.nodes[node_id]
        color = TYPE_COLOR.get(node["type"], "var(--muted)")
        parts.append(
            f'<g><rect x="{x:.0f}" y="{y:.0f}" width="{NODE_W}" height="{NODE_H}" '
            f'rx="7" fill="var(--card)" stroke="{color}" stroke-width="1.5"/>'
            f'<text class="nname" x="{x + 11:.0f}" y="{y + 20:.0f}">'
            f"{html.escape(node['name'])}</text>"
            f'<text class="ntype" x="{x + 11:.0f}" y="{y + 35:.0f}" fill="{color}">'
            f"{node['type']}</text></g>"
        )

        for i, (rtype, target) in enumerate(side.get(node_id, [])):
            color, _ = EDGE_STYLE.get(rtype, ("var(--muted)", ""))
            parts.append(
                f'<text class="chip" x="{x + 2:.0f}" '
                f'y="{y + NODE_H + 12 + i * CHIP_H:.0f}" fill="{color}">'
                f"{rtype} → {html.escape(target)}</text>"
            )

    parts.append("</svg>")
    return "".join(parts)


def build(
    model_dir: pathlib.Path,
    repo: pathlib.Path | None,
    repo_files: list[str] | None,
    contexts: list[dict],
) -> str:
    model = T.Model(model_dir)
    git = T.Git(repo)
    now = dt.datetime.now(dt.UTC)

    findings = T.validate(model, repo_files, {}, now, git)
    cov = T.coverage(model, repo_files, now) if repo_files is not None else None
    realities = [(ctx, T.resolve(model, ctx, now, git)) for ctx in contexts]
    verdict = T.integrity(findings, realities[0][1], cov)

    table = model.artifact_table()
    impacts = {loc: T.impact(model, [loc]) for loc in sorted(table)}
    if repo_files:
        for unmapped in (cov or {}).get("unmapped_files", [])[:20]:
            impacts[unmapped] = T.impact(model, [unmapped])

    e = html.escape
    system_name = model.system.get("name", model_dir.name)

    def ctx_label(ctx: dict) -> str:
        return ", ".join(f"{k}={v}" for k, v in ctx.items()) or "no context"

    reality_blocks = []
    for i, (_ctx, reality) in enumerate(realities):
        rows = []
        for subject, value in sorted(reality.items()):
            conf = value["confidence"]
            status = value["status"]
            rows.append(
                f'<tr><td class="mono">{e(subject)}</td>'
                f"<td>{e(str(value['value']) if value['value'] else '—')}</td>"
                f'<td><span class="pill {conf}">{conf}</span></td>'
                f'<td><span class="pill {"bad" if status != "RESOLVED" else "ok"}">'
                f"{status}</span></td>"
                f'<td class="mono dim">{e(", ".join(value["assertions"]))}</td></tr>'
            )
        reality_blocks.append(
            f'<div class="ctx-pane" data-ctx="{i}"{"" if i == 0 else " hidden"}>'
            f"<table><thead><tr><th>subject</th><th>resolved value</th>"
            f"<th>confidence</th><th>status</th><th>from</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )

    ctx_buttons = "".join(
        f'<button class="ctx-btn{" on" if i == 0 else ""}" data-ctx="{i}">'
        f"{e(ctx_label(ctx))}</button>"
        for i, (ctx, _) in enumerate(realities)
    )

    flow_cards = []
    downstream = {
        r["target"] for r in model.relationships if r["type"] in ("invokes", "triggers")
    }
    ordered = sorted(model.flows.items(), key=lambda kv: (kv[0] in downstream, kv[0]))
    for fid, flow in ordered:
        trig = flow.get("trigger", {})
        trig_text = trig.get("ref") or trig.get("semantic") or trig.get("actor") or ""
        outcomes = "".join(
            f'<li><span class="mono">{e(o["id"])}</span> → '
            + ", ".join(
                f"<code>{e(s['subject'])}={e(str(s['value']))}</code>"
                for s in o.get("states") or []
            )
            + "</li>"
            for o in flow.get("outcomes") or []
        )
        assertions = "".join(
            f'<li><span class="mono dim">{e(a["id"])}</span><br>{e(a["claim"])}'
            + (
                f' <span class="pill sel">when {e(json.dumps(a["when"]))}</span>'
                if a.get("when")
                else ""
            )
            + "</li>"
            for a in flow.get("assertions") or []
        )
        flow_cards.append(f"""<section class="card" id="{e(fid)}">
  <header>
    <h3>{e(fid)}</h3>
    <div class="tags">
      <span class="pill">{e(flow.get("domain", ""))}</span>
      <span class="pill {flow.get("lifecycle")}">{e(flow.get("lifecycle", ""))}</span>
      <span class="pill cov">coverage: {e(flow.get("coverage_declared", ""))}</span>
      <span class="pill trig">{e(trig.get("kind", ""))}{": " + e(trig_text) if trig_text else ""}</span>
    </div>
  </header>
  <div class="graph">{flow_svg(model, fid)}</div>
  <div class="cols">
    <div><h4>Outcomes <span class="dim">declared, bound to states</span></h4>
      <ul>{outcomes or '<li class="dim">none declared</li>'}</ul></div>
    <div><h4>Assertions</h4><ul>{assertions or '<li class="dim">none</li>'}</ul></div>
  </div>
</section>""")

    finding_rows = "".join(
        f'<tr class="{f.level}"><td><span class="pill {f.level}">{f.level}</span></td>'
        f'<td class="mono">{e(f.code)}</td><td>{e(f.message)}</td>'
        f'<td class="mono dim">{e(f.where)}</td></tr>'
        for f in findings
    )

    if cov:
        gaps = (
            "".join(f"<li class='mono'>{e(f)}</li>" for f in cov["unmapped_files"])
            or "<li class='dim'>none</li>"
        )
        stale = (
            "".join(
                f"<li class='mono'>{e(a)}</li>"
                for a in cov["assertions_without_fresh_observation"]
            )
            or "<li class='dim'>none</li>"
        )
        by_decl = ", ".join(
            f"{v} {k}" for k, v in sorted(cov["flows_by_declared_coverage"].items())
        )
        coverage_html = f"""
  <div class="cols">
    <div>
      <div class="stat"><b>{cov["flows_modeled"]}</b> flows modeled
        <span class="dim">({e(by_decl)})</span></div>
      <div class="stat"><b>{cov["artifacts_mapped"]}</b> artifacts mapped</div>
      <div class="stat"><b>{cov["artifacts_unmapped"]}</b> repository files map to
        no node</div>
    </div>
    <div><h4>Unmapped — a change here lands in <code>unknown</code></h4>
      <ul>{gaps}</ul></div>
    <div><h4>Assertions with no fresh observation</h4><ul>{stale}</ul></div>
  </div>
  <p class="note">Counts and named gaps only. No percentage is shown: full artifact
  mapping does not mean behavior is fully modeled, and a green bar here would be the
  exact false confidence this model exists to prevent (INV-012).</p>"""
    else:
        coverage_html = (
            '<p class="note">No repository file list was given, so '
            "unmodeled areas could not be detected at all (INV-010).</p>"
        )

    impact_options = "".join(
        f'<option value="{e(loc)}">{e(loc)}</option>' for loc in impacts
    )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TraceOS — {e(system_name)}</title>
<style>
:root {{
  --bg:#fbfaf8; --card:#fff; --ink:#1a1a1c; --muted:#7b7b85; --line:#e4e2dd;
  --edge:#9a97a3; --action:#3f7fbf; --decision:#c8862a; --event:#7a5bb5;
  --interaction:#2f9070; --state:#2f9070; --external:#c05c4a; --invokes:#3f7fbf;
  --emits:#7a5bb5; --triggers:#7a5bb5;
  --ok:#2f7d5a; --warn:#b0761f; --err:#b23c30;
}}
@media (prefers-color-scheme:dark) {{
  :root {{ --bg:#141416; --card:#1c1c20; --ink:#eceaea; --muted:#8e8e99;
    --line:#2c2c32; --edge:#6f6c78; --action:#6ea8e0; --decision:#e0ab5c;
    --event:#a98be0; --interaction:#5cbf9b; --state:#5cbf9b; --external:#e08a76;
    --invokes:#6ea8e0; --emits:#a98be0; --triggers:#a98be0;
    --ok:#5cbf9b; --warn:#e0ab5c; --err:#e08a76; }}
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif; }}
.wrap {{ max-width:1180px; margin:0 auto; padding:28px 22px 80px }}
h1 {{ font-size:24px; margin:0 0 4px }} h2 {{ font-size:17px; margin:34px 0 12px }}
h3 {{ font-size:15px; margin:0; font-family:ui-monospace,monospace }}
h4 {{ font-size:12px; margin:0 0 6px; text-transform:uppercase;
  letter-spacing:.06em; color:var(--muted); font-weight:600 }}
.mono, code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px }}
.dim {{ color:var(--muted) }}
.banner {{ border:1px solid var(--line); border-left:3px solid var(--warn);
  background:var(--card); padding:10px 14px; border-radius:6px; margin:16px 0 26px }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:9px;
  padding:16px 18px; margin:0 0 16px }}
.card > header {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap;
  margin-bottom:12px }}
.tags {{ display:flex; gap:6px; flex-wrap:wrap }}
.pill {{ display:inline-block; padding:1px 8px; border-radius:99px; font-size:11px;
  border:1px solid var(--line); color:var(--muted); white-space:nowrap }}
.pill.current, .pill.ok, .pill.confirmed {{ color:var(--ok); border-color:var(--ok) }}
.pill.likely, .pill.warn, .pill.cov {{ color:var(--warn); border-color:var(--warn) }}
.pill.uncertain, .pill.bad, .pill.error, .pill.err {{ color:var(--err);
  border-color:var(--err) }}
.graph {{ overflow-x:auto; padding:6px 0 10px; border-bottom:1px solid var(--line);
  margin-bottom:12px }}
svg text {{ font:12px ui-sans-serif,system-ui,sans-serif; fill:var(--ink) }}
svg .nname {{ font-weight:600 }} svg .ntype {{ font-size:10px }}
svg .cond {{ font-size:10px; fill:var(--muted) }}
svg .chip {{ font-size:10px; font-family:ui-monospace,monospace }}
.cols {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
  gap:20px }}
ul {{ margin:0; padding-left:18px }} li {{ margin-bottom:5px }}
table {{ width:100%; border-collapse:collapse; font-size:13px }}
th {{ text-align:left; font-size:11px; text-transform:uppercase; color:var(--muted);
  letter-spacing:.05em; border-bottom:1px solid var(--line); padding:5px 8px 5px 0 }}
td {{ padding:6px 8px 6px 0; border-bottom:1px solid var(--line);
  vertical-align:top }}
.ctx-btn {{ background:var(--card); border:1px solid var(--line); color:var(--muted);
  padding:5px 12px; border-radius:99px; cursor:pointer; font-size:12px;
  margin:0 6px 10px 0; font-family:inherit }}
.ctx-btn.on {{ color:var(--ink); border-color:var(--ink) }}
.tiers {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:14px; margin-top:12px }}
.tier {{ border:1px solid var(--line); border-radius:7px; padding:10px 12px }}
.tier h5 {{ margin:0 0 6px; font-size:12px; text-transform:uppercase;
  letter-spacing:.05em }}
.tier.certain h5 {{ color:var(--err) }} .tier.likely h5 {{ color:var(--warn) }}
.tier.inspect h5 {{ color:var(--action) }} .tier.unknown h5 {{ color:var(--muted) }}
.tier ul {{ padding-left:16px }} .tier li {{ font-family:ui-monospace,monospace;
  font-size:11px; margin-bottom:3px }}
select {{ font:inherit; padding:6px 10px; border-radius:6px; background:var(--card);
  color:var(--ink); border:1px solid var(--line); max-width:100% }}
.stat {{ padding:4px 0 }} .stat b {{ font-size:19px }}
.note {{ color:var(--muted); font-size:12px; margin:14px 0 0; max-width:70ch }}
.legend {{ display:flex; gap:14px; flex-wrap:wrap; font-size:11px;
  color:var(--muted); margin-bottom:14px }}
.empty {{ color:var(--muted); font-style:italic }}
</style></head><body><div class="wrap">

<h1>{e(system_name)}</h1>
<div class="dim mono">{e(str(model_dir.resolve()))} · generated {now:%Y-%m-%d %H:%M} UTC ·
integrity: <span class="pill {"ok" if verdict == "VALID" else "bad"}">{
        verdict
    }</span></div>

<div class="banner">
  <b>This page is a view, not a source of truth.</b> Regenerate it; never edit it.
  Effective reality, impact, coverage and integrity below were computed by
  <span class="mono">tools/traceos.py</span> and embedded as results — nothing is
  recomputed in the browser, so there is no second implementation to drift from the
  engine.
</div>

<h2>Effective reality <span class="dim">— derived, per context</span></h2>
<div>{ctx_buttons}</div>
{"".join(reality_blocks)}
<p class="note">Only <code>current</code> assertions resolve. A context is part of
the question: the same model answers differently for different tenants without the
graph being forked (INV-008, INV-016).</p>

<h2>Flows <span class="dim">— authored</span></h2>
<div class="legend">
  <span style="color:var(--action)">■ action</span>
  <span style="color:var(--decision)">■ decision</span>
  <span style="color:var(--event)">■ event</span>
  <span style="color:var(--interaction)">■ interaction</span>
  <span>→ <code>next</code> (arrows) · other relationships listed under each node</span>
</div>
{"".join(flow_cards)}
<p class="note">Parallel branches are drawn as the absence of a
<code>next</code> arrow, not as a fork construct (INV-021).</p>

<h2>Impact <span class="dim">— derived, four tiers</span></h2>
<div class="card">
  <select id="loc">{impact_options}</select>
  <div class="tiers" id="tiers"></div>
  <p class="note">An unmapped file lands in <code>unknown</code>, never in silence.
  <code>not mapped</code> does not mean <code>not affected</code> (INV-019).</p>
</div>

<h2>Coverage <span class="dim">— derived</span></h2>
<div class="card">{coverage_html}</div>

<h2>Validation <span class="dim">— {len(findings)} finding(s)</span></h2>
<div class="card">
  {
        "<table><thead><tr><th></th><th>code</th><th>message</th><th>where</th></tr>"
        "</thead><tbody>" + finding_rows + "</tbody></table>"
        if findings
        else '<p class="dim">no findings</p>'
    }
</div>

</div>
<script>
const IMPACT = {json.dumps(impacts)};
const tiers = document.getElementById('tiers');
const sel = document.getElementById('loc');
function render() {{
  const r = IMPACT[sel.value] || {{}};
  tiers.innerHTML = ['certain','likely','inspect','unknown'].map(t => {{
    const items = (r[t] || []);
    const body = items.length
      ? '<ul>' + items.map(x => '<li>' + x.replace(/&/g,'&amp;')
          .replace(/</g,'&lt;') + '</li>').join('') + '</ul>'
      : '<p class="dim" style="font-size:11px;margin:0">empty</p>';
    return '<div class="tier ' + t + '"><h5>' + t + ' (' + items.length + ')</h5>'
      + body + '</div>';
  }}).join('');
}}
sel.addEventListener('change', render); render();
document.querySelectorAll('.ctx-btn').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('.ctx-btn').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  document.querySelectorAll('.ctx-pane').forEach(p =>
    p.hidden = p.dataset.ctx !== b.dataset.ctx);
}}));
</script></body></html>"""


LIGHT_THEME = {
    "--card": "#ffffff",
    "--ink": "#1a1a1c",
    "--muted": "#7b7b85",
    "--edge": "#9a97a3",
    "--action": "#3f7fbf",
    "--decision": "#c8862a",
    "--event": "#7a5bb5",
    "--interaction": "#2f9070",
    "--state": "#2f9070",
    "--external": "#c05c4a",
    "--invokes": "#3f7fbf",
    "--emits": "#7a5bb5",
    "--triggers": "#7a5bb5",
}
DARK_THEME = {
    "--card": "#1c1c20",
    "--ink": "#eceaea",
    "--muted": "#8e8e99",
    "--edge": "#6f6c78",
    "--action": "#6ea8e0",
    "--decision": "#e0ab5c",
    "--event": "#a98be0",
    "--interaction": "#5cbf9b",
    "--state": "#5cbf9b",
    "--external": "#e08a76",
    "--invokes": "#6ea8e0",
    "--emits": "#a98be0",
    "--triggers": "#a98be0",
}
FONT = "ui-sans-serif,system-ui,-apple-system,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"


def standalone_svg(model: T.Model, fid: str, dark: bool = False) -> str:
    """A flow graph that survives GitHub's SVG sanitiser.

    The in-page renderer styles itself with CSS custom properties and a <style>
    block. Both are stripped when an SVG is embedded in a README, so every colour
    and font is resolved to a literal attribute here instead.
    """
    theme = DARK_THEME if dark else LIGHT_THEME
    svg = flow_svg(model, fid)
    for name, value in theme.items():
        svg = svg.replace(f"var({name})", value)
    svg = svg.replace(
        '<text class="nname"',
        f'<text font-family="{FONT}" font-size="12" font-weight="600" '
        f'fill="{theme["--ink"]}"',
    )
    svg = svg.replace('<text class="ntype"', f'<text font-family="{FONT}" font-size="10"')
    svg = svg.replace(
        '<text class="cond"',
        f'<text font-family="{FONT}" font-size="10" fill="{theme["--muted"]}"',
    )
    svg = svg.replace('<text class="chip"', f'<text font-family="{MONO}" font-size="10"')
    return svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
