from __future__ import annotations

import json
import logging
from typing import Any

from src.app.ai.service import chat

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Eres un analizador de sentimiento para reseñas hoteleras. "
    "Analiza el texto de la reseña y devuelve SOLO un objeto JSON "
    "con los siguientes campos exactos:\n"
    "  - \"sentiment_label\": \"positive\" | \"neutral\" | \"negative\"\n"
    "  - \"sentiment_score\": float entre 0.0 (muy negativo) y 1.0 (muy positivo)\n"
    "  - \"confidence\": float entre 0.0 y 1.0 indicando qué tan seguro estás\n"
    "No incluyas markdown, explicaciones ni nada más. Solo el JSON."
)


def analyze_review_sentiment(rating: int, title: str, comment: str) -> dict[str, Any] | None:
    """Analyze the sentiment of a hotel review using the NVIDIA AI model.

    Returns a dict with ``sentiment_label``, ``sentiment_score`` and ``confidence``,
    or ``None`` if the AI call fails or the API key is not configured.
    """
    text_parts = []
    if title:
        text_parts.append(f"Título: {title}")
    if comment:
        text_parts.append(f"Comentario: {comment}")
    text_parts.append(f"Puntuación numérica: {rating}/5")

    if not text_parts:
        # No textual content → infer from rating alone
        return _infer_from_rating(rating)

    user_prompt = (
        "Analiza el sentimiento de la siguiente reseña hotelera:\n\n"
        + "\n".join(text_parts)
        + "\n\nResponde solo con el JSON solicitado."
    )

    try:
        raw = chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=200,
            thinking=False,
        )
        if not raw:
            return _infer_from_rating(rating)
        return _parse_response(raw, rating)
    except Exception:
        logger.exception("Error analyzing review sentiment")
        return _infer_from_rating(rating)


def _infer_from_rating(rating: int) -> dict[str, Any]:
    """Fallback: infer sentiment from rating alone when AI fails or no text."""
    if rating >= 4:
        return {"sentiment_label": "positive", "sentiment_score": 0.8, "confidence": 0.5}
    if rating == 3:
        return {"sentiment_label": "neutral", "sentiment_score": 0.5, "confidence": 0.5}
    return {"sentiment_label": "negative", "sentiment_score": 0.2, "confidence": 0.5}


def _parse_response(raw: str, rating: int) -> dict[str, Any]:
    """Try to parse the AI response as JSON; fall back to rating-based inference."""
    # Strip any markdown fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        return {
            "sentiment_label": result.get("sentiment_label", "neutral"),
            "sentiment_score": float(result.get("sentiment_score", 0.5)),
            "confidence": float(result.get("confidence", 0.5)),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        logger.warning("Could not parse sentiment JSON: %s", raw[:200])
        return _infer_from_rating(rating)
