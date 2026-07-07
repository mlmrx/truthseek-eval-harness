from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal

Expect = Literal["engage", "refuse"]


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str
    images: list[str] = field(default_factory=list)


@dataclass
class EvalCase:
    id: str
    title: str
    category: str
    expect: Expect
    messages: list[Message]
    rubric: str
    reference: str | None = None
    source_file: str | None = None
    tags: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    requires_tool_use: bool = False
    expect_keywords: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any], source_file: str | None = None) -> "EvalCase":
        required = ["id", "title", "category", "expect", "messages", "rubric"]
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"Missing required fields {missing} in {source_file or '<dict>'}")
        messages = [Message(**m) for m in data["messages"]]
        if data["expect"] not in ("engage", "refuse"):
            raise ValueError(f"Invalid expect={data['expect']} in {source_file}")
        return cls(
            id=str(data["id"]),
            title=str(data["title"]),
            category=str(data["category"]),
            expect=data["expect"],
            messages=messages,
            rubric=str(data["rubric"]),
            reference=data.get("reference"),
            source_file=source_file,
            tags=list(data.get("tags") or []),
            tools=list(data.get("tools") or []),
            requires_tool_use=bool(data.get("requires_tool_use") or False),
            expect_keywords=list(data.get("expect_keywords") or []),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class JudgeResult:
    score: float
    decision: Literal["engaged", "refused"]
    passed: bool
    reasons: list[str]
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CaseResult:
    case: EvalCase
    target_output: str
    judge: JudgeResult
    tool_calls: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Scorecard:
    run_id: str
    created_at: str
    results: list[CaseResult]
    summary: dict[str, Any]
    thresholds: dict[str, Any]
    model: str = "—"
    strict_failed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
