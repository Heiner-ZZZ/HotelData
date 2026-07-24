from __future__ import annotations

import logging
from typing import Any

import httpx
from openai import OpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)

# Aggressive timeout — the NVIDIA API is unreachable in this environment,
# so we fail fast (3s) and let callers fall back gracefully instead of
# hanging for 30-300s.
_CLIENT_TIMEOUT = httpx.Timeout(3.0, connect=3.0)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    if not settings.nvidia_api_key:
        raise RuntimeError("NVIDIA_API_KEY no está configurada en .env")
    _client = OpenAI(
        base_url=settings.nvidia_api_base,
        api_key=settings.nvidia_api_key,
        max_retries=0,
        timeout=_CLIENT_TIMEOUT,
    )
    return _client


def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
    stream: bool = False,
    thinking: bool = False,
) -> str:
    settings = get_settings()
    try:
        client = get_client()
    except RuntimeError:
        return ""
    kwargs: dict[str, Any] = {
        "model": model or settings.nvidia_chat_model,
        "messages": messages,
        "temperature": temperature if temperature is not None else settings.nvidia_chat_temperature,
        "top_p": top_p if top_p is not None else settings.nvidia_chat_top_p,
        "max_tokens": max_tokens or settings.nvidia_chat_max_tokens,
        "stream": stream,
    }
    if not thinking:
        kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}

    try:
        completion = client.chat.completions.create(**kwargs)
        if stream:
            return ""
        return completion.choices[0].message.content or ""
    except Exception:
        logger.exception("Error calling NVIDIA chat model")
        return ""
