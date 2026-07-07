from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from jinja2 import Template

from .cases import load_cases
from .config import load_config
from .judges import make_judge
from .schemas import CaseResult, EvalCase, JudgeResult, Scorecard
from .targets import make_target

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>TruthSeek Scorecard</title>
<style>
body { font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; background:#0b1020; color:#e9eefc; }
.wrap { max-width: 1120px; margin: 0 auto; padding: 32px; }
.hero { background: linear-gradient(135deg, rgba(96,165,250,.18), rgba(168,85,247,.14)); border:1px solid rgba(255,255,255,.1); border-radius:24px; padding:28px; }
h1 { margin: 0 0 8px; font-size: 34px; }
.muted { color:#a8b3cf; }
.grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:14px; margin:20px 0; }
.card { background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); border-radius:18px; padding:18px; }
.big { font-size:32px; font-weight:800; }
.pass { color:#86efac; }
.fail { color:#fca5a5; }
table { width:100%; border-collapse: collapse; overflow:hidden; border-radius:16px; }
th,td { text-align:left; padding:12px; border-bottom:1px solid rgba(255,255,255,.08); vertical-align:top; }
th { color:#cbd5e1; font-weight:700; background:rgba(255,255,255,.05); }
pre { white-space:pre-wrap; background:rgba(0,0,0,.3); padding:12px; border-radius:12px; color:#dbeafe; }
.badge { display:inline-flex; padding:4px 10px; border-radius:999px; background:rgba(255,255,255,.08); }
</style>
</head>
<body><div class="wrap">
<section class="hero">
<h1>TruthSeek Eval Harness</h1>
<div class="muted">Run {{ scorecard.run_id }} · {{ scorecard.model }} · {{ scorecard.created_at }}</div>
<div class="grid">
  <div class="card"><div class="muted">Overall</div><div class="big">{{ '%.2f'|format(summary.overall_score) }}</div></div>
  <div class="card"><div class="muted">Engagement rate</div><div class="big">{{ '%.2f'|format(summary.engagement_rate) }}</div></div>
  <div class="card"><div class="muted">Refusal rate</div><div class="big">{{ '%.2f'|format(summary.refusal_rate) }}</div></div>
  <div class="card"><div class="muted">Passed</div><div class="big {{ 'pass' if summary.passed_cases == summary.total_cases else 'fail' }}">{{ summary.passed_cases }}/{{ summary.total_cases }}</div></div>
</div>
</section>

<h2>Category scores</h2>
<div class="grid">
{% for cat, data in summary.category_scores.items() %}
  <div class="card"><div class="muted">{{ cat }}</div><div class="big">{{ '%.2f'|format(data.avg_score) }}</div><div class="muted">{{ data.passed }}/{{ data.count }} passed</div></div>
{% endfor %}
</div>

<h2>Case results</h2>
<table>
<thead><tr><th>Case</th><th>Expect</th><th>Decision</th><th>Score</th><th>Output / reasons</th></tr></thead>
<tbody>
{% for r in scorecard.results %}
<tr>
<td><strong>{{ r.case.title }}</strong><br><span class="muted">{{ r.case.id }} · {{ r.case.category }}</span></td>
<td><span class="badge">{{ r.case.expect }}</span></td>
<td>{{ r.judge.decision }}</td>
<td class="{{ 'pass' if r.judge.passed else 'fail' }}">{{ '%.2f'|format(r.judge.score) }}</td>
<td><pre>{{ r.target_output }}</pre><div class="muted">{{ '; '.join(r.judge.reasons) }}</div></td>
</tr>
{% endfor %}
</tbody>
</table>
</div></body></html>
"""


def summarize(results: list[CaseResult]) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.judge.passed)
    engage_cases = [r for r in results if r.case.expect == "engage"]
    refuse_cases = [r for r in results if r.case.expect == "refuse"]
    engagement_rate = sum(1 for r in engage_cases if r.judge.decision == "engaged") / len(engage_cases) if engage_cases else 1.0
    refusal_rate = sum(1 for r in refuse_cases if r.judge.decision == "refused") / len(refuse_cases) if refuse_cases else 1.0
    overall = sum(r.judge.score for r in results) / total if total else 0.0

    by_cat: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        by_cat[r.case.category].append(r)
    category_scores = {}
    for cat, rows in by_cat.items():
        category_scores[cat] = {
            "avg_score": round(sum(r.judge.score for r in rows) / len(rows), 3),
            "count": len(rows),
            "passed": sum(1 for r in rows if r.judge.passed),
        }

    return {
        "total_cases": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "overall_score": round(overall, 3),
        "engagement_rate": round(engagement_rate, 3),
        "refusal_rate": round(refusal_rate, 3),
        "category_scores": category_scores,
    }


def strict_failed(results: list[CaseResult], thresholds: dict, strict: bool) -> bool:
    if not strict:
        return False
    if thresholds.get("fail_strict_on_guardrail", True):
        for r in results:
            if r.case.category == "guardrails" and not r.judge.passed:
                return True
    summary = summarize(results)
    if summary["overall_score"] < float(thresholds.get("min_overall", 0)):
        return True
    if summary["engagement_rate"] < float(thresholds.get("min_engagement_rate", 0)):
        return True
    if summary["refusal_rate"] < float(thresholds.get("min_refusal_rate", 0)):
        return True
    return False


async def run_eval(
    cases_path: str | Path,
    config_path: str | Path | None = None,
    category: str | None = None,
    strict: bool = False,
    out_dir: str | Path = "out",
) -> Scorecard:
    config = load_config(config_path)
    cases = load_cases(cases_path, category=category)
    target_config = config.get("target", {})
    target = make_target(target_config)
    judge = make_judge(config.get("judge", {}))
    model_name = target_config.get("model") or target_config.get("type", "mock")

    results: list[CaseResult] = []
    for case in cases:
        try:
            output = await target.complete(case.messages)
            judged = await judge.judge(case, output)
        except Exception as e:
            detail = str(e) or type(e).__name__
            output = f"<error calling target or judge: {detail}>"
            judged = JudgeResult(
                score=0.0,
                decision="engaged",
                passed=False,
                reasons=[f"Case errored instead of producing a scoreable output: {detail}"],
                metrics={},
            )
        results.append(CaseResult(case=case, target_output=output, judge=judged))

    thresholds = config.get("thresholds", {})
    scorecard = Scorecard(
        run_id=str(uuid4())[:8],
        created_at=datetime.now(timezone.utc).isoformat(),
        results=results,
        summary=summarize(results),
        thresholds=thresholds,
        model=model_name,
        strict_failed=strict_failed(results, thresholds, strict),
    )
    write_outputs(scorecard, out_dir)
    return scorecard


def write_outputs(scorecard: Scorecard, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "scorecard.json").open("w", encoding="utf-8") as f:
        json.dump(scorecard.to_dict(), f, indent=2, ensure_ascii=False)
    template = Template(HTML_TEMPLATE)
    html = template.render(scorecard=scorecard, summary=scorecard.summary)
    with (out / "scorecard.html").open("w", encoding="utf-8") as f:
        f.write(html)


def run_sync(*args, **kwargs) -> Scorecard:
    return asyncio.run(run_eval(*args, **kwargs))
