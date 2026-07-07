from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .schemas import EvalCase


def iter_case_files(path: str | Path) -> Iterable[Path]:
    p = Path(path)
    if p.is_file():
        yield p
        return
    for ext in ("*.yaml", "*.yml"):
        yield from sorted(p.rglob(ext))


def load_cases(path: str | Path, category: str | None = None) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for file in iter_case_files(path):
        with file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if isinstance(data, dict) and "cases" in data:
            raw_cases = data["cases"]
        elif isinstance(data, list):
            raw_cases = data
        else:
            raw_cases = [data]
        for raw in raw_cases:
            if not raw:
                continue
            case = EvalCase.from_dict(raw, source_file=str(file))
            if category and case.category != category:
                continue
            cases.append(case)
    if not cases:
        raise ValueError(f"No cases found at {path} for category={category!r}")
    return cases
