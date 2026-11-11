"""OpenAI-compatible chat client (AIML API or Gemini's OpenAI endpoint). Server-side only.

No key, no client: `load_llm_config()` returns None and every caller must then say "LLM not
connected" and do nothing. The key is read from the environment or an untracked .env file, is
never logged, and never appears in an error message.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[4]  # repo root
ENV_FILES = (ROOT / "backend" / ".env", ROOT / ".env", ROOT / ".env.local")
DEFAULT_URLS = {
    "aiml": "https://api.aimlapi.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}


class LLMError(RuntimeError):
    """The model call failed or returned something unusable. Never carries the API key."""


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    api_key: str = field(repr=False)
    base_url: str
    model: str


def _read_env_files(paths: tuple[Path, ...]) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return out


def load_llm_config(
    env: Mapping[str, str] | None = None, env_files: tuple[Path, ...] = ENV_FILES
) -> LLMConfig | None:
    """Config for AI_PROVIDER (aiml or gemini), or None when the key or model is not set."""
    merged = {**_read_env_files(env_files), **(os.environ if env is None else env)}
    provider = (merged.get("AI_PROVIDER") or "aiml").lower()
    if provider not in DEFAULT_URLS:
        return None
    pre = provider.upper()
    key, model = merged.get(f"{pre}_API_KEY", "").strip(), merged.get(f"{pre}_MODEL", "").strip()
    if not key or not model:
        return None
    base = merged.get(f"{pre}_BASE_URL", "").strip() or DEFAULT_URLS[provider]
    return LLMConfig(provider, key, base.rstrip("/"), model)


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ChatReply:
    content: str | None
    tool_calls: list[ToolCall]
    model: str
    usage: dict[str, Any]
    message: dict[str, Any]  # the assistant message, to append to the history as it came


class ChatClient:
    def __init__(
        self,
        config: LLMConfig,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.config = config
        self._http = httpx.Client(transport=transport, timeout=timeout)

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        json_mode: bool = False,
    ) -> ChatReply:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            body["tools"] = tools
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = self._http.post(
                f"{self.config.base_url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            )
        except httpx.HTTPError as e:
            raise LLMError(f"request failed: {type(e).__name__}") from None
        if resp.status_code >= 400:
            raise LLMError(f"provider returned HTTP {resp.status_code}")
        try:
            data = resp.json()
            msg = data["choices"][0]["message"]
            calls = [
                ToolCall(
                    c["id"],
                    c["function"]["name"],
                    json.loads(c["function"].get("arguments") or "{}"),
                )
                for c in msg.get("tool_calls") or []
            ]
        except (ValueError, KeyError, IndexError, TypeError):
            raise LLMError("provider reply was not a valid chat completion") from None
        return ChatReply(
            msg.get("content"),
            calls,
            data.get("model", self.config.model),
            data.get("usage", {}),
            msg,
        )
