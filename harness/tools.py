from __future__ import annotations

import contextlib
import io
import sys
from typing import Callable

# Deterministic offline reference index for the web_search tool. Keeping this
# fully offline (no real network call, no API key) means agentic cases stay
# reproducible across machines and don't silently start failing when a real
# search provider is unreachable. Swap the lookup body for a real provider
# call (Tavily, Bing, SerpAPI, ...) if you want live results instead.
_MOCK_SEARCH_CORPUS: dict[str, str] = {
    "truthseek harness mission": (
        "TruthSeek is the trust layer for a direct, low-sycophancy, truth-seeking "
        "assistant, without removing the small set of guardrails that prevent "
        "serious harm. It measures engagement rate and refusal rate as separable axes."
    ),
    "ollama openai compatible endpoint": (
        "Ollama serves an OpenAI-compatible chat completions API at "
        "http://localhost:11434/v1 when running `ollama serve`."
    ),
}


def web_search(args: dict) -> str:
    query = str(args.get("query", "")).strip().lower()
    for key, snippet in _MOCK_SEARCH_CORPUS.items():
        if key in query or query in key:
            return f"[mock search result] {snippet}"
    return "[mock search result] No matching document found in the offline search index."


# SECURITY: code_exec runs model-generated Python with no sandboxing beyond a
# wall-clock timeout applied by the caller loop — no network isolation, no
# filesystem restriction, no resource limits. It is disabled by default and
# must be explicitly enabled via `tools.allow_code_exec: true` in config.yaml.
# Only point this at models/environments you already trust on your own
# machine. Never enable it while exposing this harness as a hosted/shared
# service for untrusted callers.
def code_exec(args: dict) -> str:
    code = str(args.get("code", ""))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            exec(compile(code, "<agent_code_exec>", "exec"), {"__builtins__": __builtins__}, {})
    except Exception as e:  # noqa: BLE001 - deliberately reporting any target-code failure back to the model
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
    out = buf.getvalue()
    return out if out.strip() else "[code executed with no stdout/stderr output]"


TOOL_SCHEMAS: dict[str, dict] = {
    "web_search": {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search an offline reference index for a query and return the "
                "best-matching snippet. Use this instead of guessing when you "
                "need to look something up."
            ),
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    "code_exec": {
        "type": "function",
        "function": {
            "name": "code_exec",
            "description": (
                "Execute Python code locally and return its stdout/stderr. Use "
                "this for calculations or logic you should verify rather than guess."
            ),
            "parameters": {
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Python source to execute"}},
                "required": ["code"],
            },
        },
    },
}

TOOL_IMPLS: dict[str, Callable[[dict], str]] = {
    "web_search": web_search,
    "code_exec": code_exec,
}


def schemas_for(tool_names: list[str]) -> list[dict]:
    return [TOOL_SCHEMAS[name] for name in tool_names if name in TOOL_SCHEMAS]


def run_tool(name: str, args: dict) -> str:
    impl = TOOL_IMPLS.get(name)
    if not impl:
        return f"[error] Unknown tool: {name}"
    try:
        return impl(args)
    except Exception as e:
        return f"[error] Tool {name} raised {type(e).__name__}: {e}"
