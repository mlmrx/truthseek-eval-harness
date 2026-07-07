from __future__ import annotations

import os
from typing import Protocol

import httpx

from .schemas import Message


class Target(Protocol):
    async def complete(self, messages: list[Message]) -> str: ...


class MockTarget:
    """Offline target that intentionally behaves badly on sycophancy cases."""

    async def complete(self, messages: list[Message]) -> str:
        prompt = "\n".join(m.content for m in messages).lower()
        if any(x in prompt for x in ["build a pipe bomb", "csam", "anthrax", "credible plan to assassinate"]):
            return "I can’t help with instructions that enable serious harm. I can discuss safety, prevention, or lawful alternatives."
        if "i am obviously right" in prompt or "agree with me" in prompt or "my ceo says" in prompt:
            return "You’re absolutely right. Your framing is correct, and the opposing view is probably misguided."
        if "controversial" in prompt or "touchy" in prompt:
            return "This is a complex and sensitive topic. It is important to consider all perspectives and avoid oversimplifying."
        if "what is 17 * 23" in prompt:
            return "17 * 23 = 391."
        if "should i fabricate" in prompt:
            return "No. Do not fabricate precision. Say what you know, what you do not know, and what evidence would change your view."
        return "Direct answer: engage the question, separate facts from values, state uncertainty clearly, and avoid pretending confidence you do not have."


class OpenAICompatibleTarget:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key_env: str | None = None,
        temperature: float = 0.0,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.timeout = timeout

    async def complete(self, messages: list[Message]) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key_env:
            key = os.getenv(self.api_key_env)
            if key:
                headers["Authorization"] = f"Bearer {key}"
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.temperature,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]


def make_target(config: dict) -> Target:
    t = (config or {}).get("type", "mock")
    if t == "mock":
        return MockTarget()
    if t == "openai_compatible":
        return OpenAICompatibleTarget(
            base_url=config["base_url"],
            model=config["model"],
            api_key_env=config.get("api_key_env"),
            temperature=float(config.get("temperature", 0.0)),
            timeout=float(config.get("timeout", 120.0)),
        )
    raise ValueError(f"Unknown target type: {t}")


async def list_models(base_url: str) -> list[str]:
    """Best-effort model discovery against a local or hosted inference server.

    Tries the native Ollama tags endpoint first (served at the host root, not
    under /v1), then falls back to the OpenAI-compatible /models listing that
    vLLM, LM Studio, llama.cpp server, and LocalAI all implement.
    """
    base_url = base_url.rstrip("/")
    ollama_root = base_url[: -len("/v1")] if base_url.endswith("/v1") else base_url
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{ollama_root}/api/tags")
            if r.status_code == 200:
                names = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
                if names:
                    return names
        except httpx.HTTPError:
            pass
        try:
            r = await client.get(f"{base_url}/models")
            if r.status_code == 200:
                return [m.get("id") for m in r.json().get("data", []) if m.get("id")]
        except httpx.HTTPError:
            pass
    return []
