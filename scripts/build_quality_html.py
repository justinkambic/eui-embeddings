#!/usr/bin/env python3
"""Render a static HTML page summarizing the latest quality sweep.

Reads the most recent `reports/quality_<version>_<ts>/report.json`
and produces `reports/quality_<version>.html` — one row per icon,
alphabetical, with the canonical icon rendered inline (base64 PNG)
plus the rank, self-score, top hit, and score gap from the sweep.

Self-contained: PNGs are inlined so the file can be moved/shared
without any companion files.

Usage:
    .venv-mcp/bin/python scripts/build_quality_html.py --version v115.0.0
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

log = logging.getLogger("build_quality_html")


def find_latest_report(version: str) -> Path:
    candidates = sorted(
        (REPO_ROOT / "reports").glob(f"quality_{version}_*"),
        key=lambda p: p.name,
        reverse=True,
    )
    for c in candidates:
        if (c / "report.json").exists():
            return c / "report.json"
    raise FileNotFoundError(f"no quality report found for {version}")


def rank_class(r: dict) -> str:
    rank = r["rank"]
    if r.get("error") and rank == -2:
        return "skipped"
    if r.get("error"):
        return "errored"
    if rank == 1:
        return "rank-1"
    if rank in (2, 3):
        return "rank-23"
    if rank > 0 and rank <= 10:
        return "rank-410"
    if rank > 0 and rank <= 50:
        return "rank-50"
    return "miss"


def rank_label(r: dict) -> str:
    rank = r["rank"]
    if rank == -2:
        return "skipped"
    if r.get("error"):
        return "error"
    if rank == -1:
        return "miss"
    return f"#{rank}"


def render_icon_cell(prop: str, png_dir: Path) -> str:
    p = png_dir / f"{prop}.png"
    if not p.exists():
        return '<div class="no-png">—</div>'
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f'<img alt="{html.escape(prop)}" src="data:image/png;base64,{b64}">'


def render_html(report: dict, png_dir: Path, version: str) -> str:
    summary = report["summary"]
    results = sorted(report["results"], key=lambda r: r["prop_name"].lower())

    base = max(summary["evaluated"], 1)
    pct_top1 = summary["ranked_top_1"] / base * 100
    pct_top3 = summary["ranked_top_3"] / base * 100
    pct_top10 = summary["ranked_top_10"] / base * 100

    rows: list[str] = []
    for r in results:
        prop = r["prop_name"]
        cls = rank_class(r)
        rank = rank_label(r)
        self_score = (
            f"{r['self_score']:.3f}" if r.get("self_score") is not None else "—"
        )
        top_hit = r.get("top_hit") or "—"
        top_score = (
            f"{r['top_score']:.3f}" if r.get("top_score") is not None else "—"
        )
        gap = (
            f"{r['score_gap']:+.3f}" if r.get("score_gap") is not None else "—"
        )
        # Highlight top hit when it's wrong; show only when rank > 1.
        top_hit_cell = (
            "—"
            if r["rank"] == 1 or r.get("error") or r["rank"] == -2
            else f'<code>{html.escape(top_hit)}</code>'
        )
        gap_cell = "—" if r["rank"] == 1 or r.get("error") or r["rank"] == -2 else gap

        # Competitors (top-3 wrong-asset hits, when present)
        competitors = ""
        if r["rank"] != 1 and r.get("competitors"):
            top_competitors = r["competitors"][:3]
            competitors = ", ".join(
                f'<code>{html.escape(c["prop_name"])}</code>&nbsp;{c["score"]:.3f}'
                for c in top_competitors
            )

        rows.append(
            f"""<tr class="{cls}">
  <td class="icon">{render_icon_cell(prop, png_dir)}</td>
  <td class="prop"><code>{html.escape(prop)}</code></td>
  <td class="rank">{rank}</td>
  <td class="score">{self_score}</td>
  <td class="top-hit">{top_hit_cell}</td>
  <td class="gap">{gap_cell}</td>
  <td class="competitors">{competitors}</td>
</tr>"""
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EUI icon search quality — {version}</title>
<style>
  :root {{
    color-scheme: light dark;
    --bg: #fafafa;
    --fg: #1a1a1a;
    --muted: #666;
    --rank-1: #d4f4dd;
    --rank-23: #eaf6e3;
    --rank-410: #fff3cd;
    --rank-50: #ffe0b3;
    --miss: #ffd6d6;
    --skipped: #e8e8e8;
    --errored: #ffd6d6;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1a1a1a;
      --fg: #f0f0f0;
      --muted: #999;
      --rank-1: #1f3a25;
      --rank-23: #243a25;
      --rank-410: #3d3415;
      --rank-50: #3d2913;
      --miss: #3a1f1f;
      --skipped: #2a2a2a;
      --errored: #3a1f1f;
    }}
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: var(--bg);
    color: var(--fg);
    margin: 0;
    padding: 24px;
  }}
  header {{
    max-width: 1100px;
    margin: 0 auto 24px;
  }}
  h1 {{ margin: 0 0 8px; font-size: 22px; }}
  .meta {{ color: var(--muted); font-size: 13px; }}
  .summary {{
    margin: 16px 0 24px;
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    font-size: 14px;
  }}
  .summary > div {{
    background: rgba(127,127,127,0.1);
    padding: 10px 16px;
    border-radius: 8px;
    min-width: 140px;
  }}
  .summary .label {{ color: var(--muted); font-size: 12px; }}
  .summary .value {{ font-size: 18px; font-weight: 600; }}
  .legend {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 12px 0 24px;
    font-size: 12px;
  }}
  .legend span {{
    padding: 4px 10px;
    border-radius: 4px;
  }}
  .legend .rank-1 {{ background: var(--rank-1); }}
  .legend .rank-23 {{ background: var(--rank-23); }}
  .legend .rank-410 {{ background: var(--rank-410); }}
  .legend .rank-50 {{ background: var(--rank-50); }}
  .legend .miss {{ background: var(--miss); }}
  .legend .skipped {{ background: var(--skipped); }}
  table {{
    border-collapse: collapse;
    width: 100%;
    max-width: 1100px;
    margin: 0 auto;
    background: var(--bg);
  }}
  th, td {{
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid rgba(127,127,127,0.2);
    vertical-align: middle;
    font-size: 13px;
  }}
  th {{
    position: sticky;
    top: 0;
    background: var(--bg);
    z-index: 1;
    border-bottom: 2px solid rgba(127,127,127,0.4);
  }}
  td.icon {{ width: 40px; text-align: center; }}
  td.icon img {{
    width: 28px;
    height: 28px;
    object-fit: contain;
    background: white;
    border-radius: 4px;
    padding: 2px;
  }}
  td.icon .no-png {{ color: var(--muted); }}
  td.prop {{ width: 220px; }}
  td.rank {{ width: 70px; font-weight: 600; }}
  td.score {{ width: 70px; font-variant-numeric: tabular-nums; }}
  td.top-hit {{ width: 200px; }}
  td.gap {{ width: 80px; font-variant-numeric: tabular-nums; }}
  td.competitors {{ font-size: 12px; color: var(--muted); }}
  tr.rank-1 {{ background: var(--rank-1); }}
  tr.rank-23 {{ background: var(--rank-23); }}
  tr.rank-410 {{ background: var(--rank-410); }}
  tr.rank-50 {{ background: var(--rank-50); }}
  tr.miss {{ background: var(--miss); }}
  tr.skipped {{ background: var(--skipped); color: var(--muted); }}
  tr.errored {{ background: var(--errored); color: var(--muted); }}
  code {{
    background: rgba(127,127,127,0.18);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 12px;
    font-family: ui-monospace, "SF Mono", Menlo, monospace;
  }}
  input[type="text"] {{
    width: 240px;
    padding: 6px 8px;
    border: 1px solid rgba(127,127,127,0.4);
    border-radius: 6px;
    background: var(--bg);
    color: var(--fg);
    font-size: 13px;
  }}
</style>
</head>
<body>
<header>
  <h1>EUI icon search quality — {version}</h1>
  <div class="meta">Generated {html.escape(report['generated_at'])} · {summary['evaluated']} icons evaluated</div>
  <div class="summary">
    <div><div class="label">Top-1</div><div class="value">{pct_top1:.1f}%</div><div class="meta">{summary['ranked_top_1']} / {summary['evaluated']}</div></div>
    <div><div class="label">Top-3</div><div class="value">{pct_top3:.1f}%</div><div class="meta">{summary['ranked_top_3']} / {summary['evaluated']}</div></div>
    <div><div class="label">Top-10</div><div class="value">{pct_top10:.1f}%</div><div class="meta">{summary['ranked_top_10']} / {summary['evaluated']}</div></div>
    <div><div class="label">Misses (≥50)</div><div class="value">{summary['not_in_top_50']}</div><div class="meta">unrecoverable</div></div>
    <div><div class="label">Skipped</div><div class="value">{summary['skipped']}</div><div class="meta">no PNG</div></div>
  </div>
  <div class="legend">
    <span class="rank-1">#1 (correct top hit)</span>
    <span class="rank-23">#2–3</span>
    <span class="rank-410">#4–10</span>
    <span class="rank-50">#11–50</span>
    <span class="miss">miss / not in top 50</span>
    <span class="skipped">skipped (no PNG)</span>
  </div>
  <input type="text" id="filter" placeholder="filter by prop name…" oninput="filterRows(this.value)">
</header>
<table>
<thead>
<tr>
  <th></th>
  <th>prop</th>
  <th>rank</th>
  <th>score</th>
  <th>top hit (when rank &gt; 1)</th>
  <th>Δ</th>
  <th>closest competitors</th>
</tr>
</thead>
<tbody id="rows">
{chr(10).join(rows)}
</tbody>
</table>
<script>
  function filterRows(q) {{
    q = q.toLowerCase();
    for (const row of document.querySelectorAll('#rows tr')) {{
      const propText = row.querySelector('td.prop').innerText.toLowerCase();
      row.style.display = propText.includes(q) ? '' : 'none';
    }}
  }}
</script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--version", default="v115.0.0")
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="explicit path to report.json; otherwise picks the latest",
    )
    parser.add_argument(
        "--png-dir",
        type=Path,
        default=None,
        help="dir of <prop>.png files; defaults to reports/resvg_pngs_<version>",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="output HTML path; defaults to reports/quality_<version>.html",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    report_path = args.report or find_latest_report(args.version)
    log.info("reading %s", report_path)
    report = json.loads(report_path.read_text())

    png_dir = args.png_dir or REPO_ROOT / "reports" / f"resvg_pngs_{args.version}"
    if not png_dir.is_dir():
        log.error("png-dir not found: %s", png_dir)
        return 2
    log.info("inlining PNGs from %s", png_dir)

    out = args.out or REPO_ROOT / "reports" / f"quality_{args.version}.html"
    out.write_text(render_html(report, png_dir, args.version), encoding="utf-8")
    log.info("wrote %s (%d KB)", out, out.stat().st_size // 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
