from __future__ import annotations

import html
import math
from datetime import datetime, timezone

from brief import __version__ as BRIEF_VERSION
from brief.generator.schema import GeneratedDescription, QualityRubric
from brief.scanner.models import AppScanReport, ObjectSignals
from brief.scoring.score import AppScore, ObjectScore


def generate_html_report(
    report: AppScanReport,
    score: AppScore,
    descriptions: dict[str, GeneratedDescription],
    quality_rubrics: dict[str, QualityRubric],
) -> str:
    saved_searches = [o for o in report.objects if o.object_type == "savedsearch"]
    described_count = sum(1 for o in saved_searches if o.description_present)
    callable_now = sum(
        1 for o in saved_searches if o.description_present and not o.safety.violations
    )
    obj_by_name: dict[str, ObjectSignals] = {o.name: o for o in saved_searches}

    worst = min(score.objects, key=lambda o: o.composite, default=None)
    worst_signal = obj_by_name.get(worst.object_name) if worst is not None else None

    body_sections = [
        _hero(report),
        _score_hero(score, callable_now, len(saved_searches)),
        _subscores(score),
        _file_table(score),
        _before_after(worst, worst_signal, descriptions) if worst_signal else "",
        _object_table(saved_searches, score.objects, descriptions, quality_rubrics),
        _footer(report),
    ]

    return _PAGE.format(
        title=html.escape(f"Brief — {report.app_name}"),
        body="\n".join(s for s in body_sections if s),
    )


def _hero(report: AppScanReport) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    app_desc = html.escape(report.app_description or "")
    version = html.escape(report.app_version or "")
    return f"""<section class="hero">
  <div class="meta-line">brief · agent-readiness audit · {html.escape(generated_at)}</div>
  <h1 class="display">{html.escape(report.app_name)}<span class="period">.</span></h1>
  {f'<p class="subtitle">{app_desc}</p>' if app_desc else ''}
  {f'<p class="byline">version {version}</p>' if version else ''}
</section>"""


def _score_hero(score: AppScore, callable_now: int, total_searches: int) -> str:
    circ = 2 * math.pi * 50
    offset = circ * (1 - score.overall_score / 100)
    return f"""<section class="score-hero">
  <div class="score-ring">
    <svg viewBox="0 0 120 120" width="220" height="220">
      <circle cx="60" cy="60" r="50" fill="none" stroke="#E5DFD3" stroke-width="6"/>
      <circle cx="60" cy="60" r="50" fill="none" stroke="#B5731E" stroke-width="6"
              stroke-linecap="round"
              stroke-dasharray="{circ:.2f}" stroke-dashoffset="{offset:.2f}"
              transform="rotate(-90 60 60)"/>
      <text x="60" y="70" text-anchor="middle" font-family="Instrument Serif, serif"
            font-size="44" fill="#1A1611">{score.overall_score}</text>
    </svg>
  </div>
  <div class="score-meta">
    <div class="score-label">Overall agent-readiness</div>
    <div class="score-detail">An AI agent can routinely call <strong>{callable_now}</strong> of <strong>{total_searches}</strong> saved searches today.</div>
  </div>
</section>"""


def _subscores(score: AppScore) -> str:
    cards = [
        ("Presence", score.presence_pct, "Searches that have a description at all."),
        ("Quality", score.quality_avg, "Average rubric score across described searches."),
        ("Coverage", score.coverage_pct, "File-level coverage; rewards complete files."),
        ("Safety", score.safety_pct, "Lower with destructive SPL or unbounded queries."),
    ]
    cells = "\n".join(
        f"""  <div class="subscore">
    <div class="subscore-value">{value}</div>
    <div class="subscore-label">{label}</div>
    <div class="subscore-note">{note}</div>
  </div>"""
        for label, value, note in cards
    )
    return f"""<section class="subscores">
{cells}
</section>"""


def _file_table(score: AppScore) -> str:
    if not score.files:
        return ""
    rows = "\n".join(
        f"""    <tr>
      <td><code>{html.escape(f.file_name)}</code></td>
      <td class="num">{round(f.coverage * 100)}%</td>
      <td class="num">{round(f.avg_quality * 100)}%</td>
      <td class="num"><strong>{round(f.composite * 100)}</strong></td>
    </tr>"""
        for f in score.files
    )
    return f"""<section>
  <div class="section-num">§ Per-file rollup</div>
  <h2>Coverage by file.</h2>
  <table>
    <thead>
      <tr><th>file</th><th>coverage</th><th>quality</th><th>composite</th></tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</section>"""


def _before_after(
    worst: ObjectScore,
    obj: ObjectSignals,
    descriptions: dict[str, GeneratedDescription],
) -> str:
    before_text = (
        html.escape(obj.description_text)
        if obj.description_text
        else "<em>(no description in savedsearches.conf)</em>"
    )
    after_html = ""
    if obj.name in descriptions:
        d = descriptions[obj.name]
        mitre = (
            f'<div class="mitre">{" ".join(_tag(t, "amber") for t in d.mitre_techniques)}</div>'
            if d.mitre_techniques
            else ""
        )
        after_html = f"""<div class="after-card">
      <div class="after-label">Brief proposes</div>
      <p class="after-desc">{html.escape(d.description)}</p>
      <div class="after-meta">
        <span class="kv"><strong>use case</strong> {html.escape(d.primary_use_case)}</span>
        <span class="kv"><strong>runtime</strong> {d.estimated_runtime}</span>
        <span class="kv"><strong>fields</strong> {html.escape(", ".join(d.output_fields))}</span>
      </div>
      {mitre}
    </div>"""

    pre_spl = html.escape(obj.raw_definition.strip())
    return f"""<section>
  <div class="section-num">§ Worst-scoring object</div>
  <h2><span class="ident">{html.escape(obj.name)}</span></h2>
  <p>Composite <strong>{round(worst.composite * 100)}/100</strong> — driven by presence {round(worst.presence * 100)}, quality {round(worst.quality * 100)}, safety {round(worst.safety * 100)}.</p>
  <details open>
    <summary>Show SPL and proposed description</summary>
    <pre class="spl">{pre_spl}</pre>
    <div class="before-card">
      <div class="before-label">Currently</div>
      <p class="before-desc">{before_text}</p>
    </div>
    {after_html}
  </details>
</section>"""


def _object_table(
    objects: list[ObjectSignals],
    object_scores: list[ObjectScore],
    descriptions: dict[str, GeneratedDescription],
    quality_rubrics: dict[str, QualityRubric],
) -> str:
    scores_by_name = {s.object_name: s for s in object_scores}
    rows: list[str] = []
    for obj in objects:
        s = scores_by_name.get(obj.name)
        if s is None:
            continue
        status = "described" if obj.description_present else "missing"
        status_class = "tag" if obj.description_present else "tag amber"
        if obj.name in descriptions:
            proposed = descriptions[obj.name].description
            proposed_cell = (
                f'<div class="proposed">{html.escape(proposed[:140])}'
                + ("…" if len(proposed) > 140 else "")
                + "</div>"
            )
        elif obj.description_text:
            proposed_cell = (
                f'<div class="proposed">{html.escape(obj.description_text[:140])}'
                + ("…" if len(obj.description_text) > 140 else "")
                + "</div>"
            )
        else:
            proposed_cell = '<span class="dim">—</span>'

        safety_tag = (
            _tag("safe", "")
            if not obj.safety.violations and not obj.safety.warnings
            else _tag("warnings", "amber")
            if not obj.safety.violations
            else _tag("violations", "red")
        )

        rubric = quality_rubrics.get(obj.name)
        quality_cell = (
            f"{rubric.quality_score}/10" if rubric else '<span class="dim">—</span>'
        )

        rows.append(
            f"""    <tr>
      <td><code>{html.escape(obj.name)}</code></td>
      <td><span class="{status_class}">{status}</span></td>
      <td>{proposed_cell}</td>
      <td>{quality_cell}</td>
      <td>{safety_tag}</td>
    </tr>"""
        )

    rows_html = "\n".join(rows)
    return f"""<section>
  <div class="section-num">§ Per-object readiness</div>
  <h2>What Brief found.</h2>
  <table class="object-table">
    <thead>
      <tr><th>saved search</th><th>status</th><th>description</th><th>quality</th><th>safety</th></tr>
    </thead>
    <tbody>
{rows_html}
    </tbody>
  </table>
</section>"""


def _footer(report: AppScanReport) -> str:
    return f"""<footer>
  Generated by <strong>brief v{BRIEF_VERSION}</strong> · {len(report.objects)} objects scanned · zero input files modified.
</footer>"""


def _tag(text: str, color: str) -> str:
    classes = "tag " + color if color else "tag"
    return f'<span class="{classes.strip()}">{html.escape(text)}</span>'


_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Geist:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: 'Geist', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 16px;
  line-height: 1.65;
  color: #1A1611;
  background: #FAF7F2;
  font-feature-settings: "ss01","ss03","kern";
}}
.container {{
  max-width: 880px;
  margin: 0 auto;
  padding: 60px 36px 120px;
}}
.meta-line {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #8A8175;
  margin: 0 0 28px;
  display: flex;
  gap: 12px;
  align-items: center;
}}
.meta-line::before {{
  content: "";
  width: 8px; height: 8px;
  background: #B5731E;
  border-radius: 50%;
}}
.hero {{ margin-bottom: 60px; padding-bottom: 40px; border-bottom: 0.5px solid #E5DFD3; }}
.display {{
  font-family: 'Instrument Serif', Georgia, serif;
  font-size: clamp(64px, 9vw, 112px);
  line-height: 0.92;
  letter-spacing: -0.03em;
  margin: 0 0 24px;
  font-weight: 400;
}}
.display .period {{ color: #B5731E; }}
.subtitle {{
  font-family: 'Instrument Serif', serif;
  font-size: clamp(20px, 2.6vw, 26px);
  line-height: 1.3;
  font-style: italic;
  color: #4A4339;
  margin: 0 0 12px;
  max-width: 640px;
}}
.byline {{ color: #8A8175; font-size: 13px; margin: 0; }}

.score-hero {{
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 36px;
  align-items: center;
  margin: 56px 0;
  padding: 32px 0;
}}
.score-meta .score-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #B5731E;
  margin-bottom: 14px;
}}
.score-meta .score-detail {{
  font-family: 'Instrument Serif', serif;
  font-size: 26px;
  font-style: italic;
  line-height: 1.35;
  color: #1A1611;
}}

.subscores {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin: 40px 0 60px;
}}
.subscore {{
  padding: 22px 20px;
  background: #FAF6EE;
  border: 0.5px solid #E5DFD3;
  border-radius: 4px;
}}
.subscore-value {{
  font-family: 'Instrument Serif', serif;
  font-size: 44px;
  line-height: 1;
  color: #1A1611;
  margin-bottom: 6px;
}}
.subscore-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #4A4339;
  margin-bottom: 8px;
}}
.subscore-note {{
  font-size: 12px;
  color: #8A8175;
  line-height: 1.5;
}}

section {{ margin: 72px 0; }}
.section-num {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.18em;
  color: #B5731E;
  margin: 0 0 14px;
  text-transform: uppercase;
}}
h2 {{
  font-family: 'Instrument Serif', serif;
  font-size: clamp(30px, 4vw, 40px);
  line-height: 1.08;
  letter-spacing: -0.02em;
  font-weight: 400;
  margin: 0 0 28px;
}}
h2 .ident {{ font-family: 'JetBrains Mono', monospace; font-size: 0.7em; color: #4A4339; }}
p {{ margin: 0 0 20px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin: 12px 0; }}
th, td {{ text-align: left; padding: 12px 14px; border-bottom: 0.5px solid #E5DFD3; vertical-align: top; }}
th {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #1A1611;
  border-bottom: 1px solid #1A1611;
}}
td.num {{ font-family: 'JetBrains Mono', monospace; text-align: right; }}
code {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  background: #F1EBE0;
  padding: 2px 6px;
  border-radius: 3px;
  color: #5C4B33;
}}
.tag {{
  display: inline-block;
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.06em;
  color: #4F6B5C;
  border: 0.5px solid #4F6B5C;
  padding: 2px 7px;
  border-radius: 3px;
}}
.tag.amber {{ color: #8A5612; border-color: #B5731E; }}
.tag.red    {{ color: #791F1F; border-color: #A32D2D; }}
.dim {{ color: #8A8175; }}

details {{ margin: 16px 0 0; }}
summary {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.06em;
  color: #4A4339;
  cursor: pointer;
  padding: 8px 0;
}}
summary::marker {{ color: #B5731E; }}
pre.spl {{
  background: #F1EBE0;
  border-left: 2px solid #4F6B5C;
  border-radius: 4px;
  padding: 18px 22px;
  margin: 16px 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12.5px;
  line-height: 1.65;
  color: #3A3128;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}}

.before-card, .after-card {{
  padding: 20px 24px;
  border-radius: 4px;
  margin: 14px 0;
}}
.before-card {{ background: #FCEBEB; border-left: 2px solid #A32D2D; }}
.after-card  {{ background: #F8F2E6; border-left: 2px solid #B5731E; }}
.before-label, .after-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #B5731E;
  margin-bottom: 6px;
}}
.before-label {{ color: #A32D2D; }}
.before-desc, .after-desc {{ font-family: 'Instrument Serif', serif; font-size: 19px; line-height: 1.45; margin: 0 0 12px; color: #1A1611; font-style: italic; }}
.after-meta {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: 12.5px; }}
.kv {{ color: #4A4339; }}
.kv strong {{ font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: 0.12em; text-transform: uppercase; color: #B5731E; margin-right: 6px; }}
.mitre {{ margin-top: 10px; }}
.proposed {{ font-size: 13px; color: #2A2520; line-height: 1.55; }}

footer {{
  margin-top: 100px;
  padding-top: 28px;
  border-top: 0.5px solid #E5DFD3;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  letter-spacing: 0.06em;
  color: #8A8175;
}}

@media (max-width: 720px) {{
  .container {{ padding: 40px 20px 80px; }}
  .score-hero {{ grid-template-columns: 1fr; gap: 16px; text-align: center; }}
  .subscores {{ grid-template-columns: repeat(2, 1fr); }}
  table {{ font-size: 12.5px; }}
}}
</style>
</head>
<body>
<div class="container">
{body}
</div>
</body>
</html>
"""
