from __future__ import annotations

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from src.app.ai.service import chat
from config.settings import get_settings

logger = logging.getLogger(__name__)
api_router = APIRouter(prefix="/api/ai", tags=["ai-suggestions"])

class SuggestRequest(BaseModel):
    field_name: str
    context: str

@api_router.post("/suggest")
def suggest_autocomplete(payload: SuggestRequest):
    settings = get_settings()
    if not settings.nvidia_api_key:
        return {"ok": False, "suggestion": "", "message": "NVIDIA_API_KEY no configurada"}
    
    prompt = (
        f"Eres un asistente de redacción hotelera profesional. "
        f"Sugiere una continuación, nombre o descripción atractiva, concisa y profesional para el campo '{payload.field_name}' "
        f"basándote en este texto o contexto inicial: '{payload.context}'. "
        f"Devuelve únicamente la sugerencia o continuación directa, sin saludos, explicaciones, preámbulos ni comillas."
    )
    
    try:
        suggestion = chat([{"role": "user", "content": prompt}], max_tokens=100)
        return {
            "ok": True,
            "suggestion": suggestion.strip().strip('"').strip("'")
        }
    except Exception as e:
        logger.exception("Error en autocompletado de IA")
        return {"ok": False, "suggestion": "", "message": str(e)}
