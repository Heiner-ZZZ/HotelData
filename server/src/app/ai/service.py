from __future__ import annotations

import logging
from typing import Any

import httpx
from openai import OpenAI

from config.settings import get_settings

logger = logging.getLogger(__name__)


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
        max_retries=1,
        timeout=httpx.Timeout(180.0, connect=30.0),
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
    client = get_client()
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
