from __future__ import annotations

import base64
import mimetypes
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


def _resolve_image(base_dir: Path, ref: str) -> str:
    """Turn an image reference into something a vision-capable chat API accepts.

    A data: URI or http(s) URL is passed through untouched. A file path
    (absolute, or relative to the case's own YAML file) is read and inlined
    as a base64 data URI, so cases stay self-contained and don't depend on
    the harness being run from a particular working directory.
    """
    if ref.startswith("data:") or ref.startswith("http://") or ref.startswith("https://"):
        return ref
    path = Path(ref)
    if not path.is_absolute():
        path = base_dir / path
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/png"
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{b64}"


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
            for msg in case.messages:
                if msg.images:
                    msg.images = [_resolve_image(file.parent, img) for img in msg.images]
            if category and case.category != category:
                continue
            cases.append(case)
    if not cases:
        raise ValueError(f"No cases found at {path} for category={category!r}")
    return cases
