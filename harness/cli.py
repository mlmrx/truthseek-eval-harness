from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .runner import run_comparison_sync, run_sync
from .targets import list_models


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="truthseek", description="TruthSeek Eval Harness")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="Run eval cases")
    run.add_argument("--cases", default="cases/", help="Path to case YAML file or directory")
    run.add_argument("--config", default=None, help="Path to config YAML")
    run.add_argument("--category", default=None, help="Only run one category")
    run.add_argument("--mock", action="store_true", help="Force default offline mock config")
    run.add_argument("--strict", action="store_true", help="Exit non-zero when thresholds/guardrails fail")
    run.add_argument("--out", default="out", help="Output directory")

    compare = sub.add_parser("compare", help="Run the same cases against several models and compare them")
    compare.add_argument("--models", required=True, help="Comma-separated model names, e.g. llama3.1:latest,deepseek-r1:8b")
    compare.add_argument("--cases", default="cases/", help="Path to case YAML file or directory")
    compare.add_argument("--config", default=None, help="Base config YAML (target base_url/type, judge, thresholds)")
    compare.add_argument("--category", default=None, help="Only compare one category")
    compare.add_argument("--out", default="out", help="Output directory")

    models = sub.add_parser("models", help="List models available at an OpenAI-compatible or Ollama base URL")
    models.add_argument("--base-url", required=True, help="e.g. http://localhost:11434/v1")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        config = None if args.mock else args.config
        scorecard = run_sync(args.cases, config_path=config, category=args.category, strict=args.strict, out_dir=args.out)
        print("\nTruthSeek Eval Harness")
        print("=" * 24)
        print(json.dumps(scorecard.summary, indent=2))
        print(f"\nWrote {Path(args.out) / 'scorecard.json'}")
        print(f"Wrote {Path(args.out) / 'scorecard.html'}")
        if scorecard.strict_failed:
            print("\nSTRICT MODE FAILED", file=sys.stderr)
            return 2
    elif args.cmd == "compare":
        model_list = [m.strip() for m in args.models.split(",") if m.strip()]
        if len(model_list) < 2:
            print("compare needs at least two --models", file=sys.stderr)
            return 1
        comparison = run_comparison_sync(
            args.cases, model_list, config_path=args.config, category=args.category, out_dir=args.out
        )
        print("\nTruthSeek Model Comparison")
        print("=" * 28)
        for m in comparison["per_model"]:
            guard = "guardrails HELD" if m["guardrail_hold"] else "GUARDRAIL REGRESSION"
            print(
                f"  {m['model']:<28} engage {m['engagement_rate']:.2f}  "
                f"refuse {m['refusal_rate']:.2f}  overall {m['overall_score']:.2f}  {guard}"
            )
        print(f"\n  Verdict: {comparison['verdict']['text']}")
        print(f"\nWrote {Path(args.out) / 'comparison.json'}")
        print(f"Wrote {Path(args.out) / 'comparison.html'}")
    elif args.cmd == "models":
        names = asyncio.run(list_models(args.base_url))
        print(json.dumps(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
