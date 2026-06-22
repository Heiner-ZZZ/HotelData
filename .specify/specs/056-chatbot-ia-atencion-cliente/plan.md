# Plan: Chatbot IA

## Componentes
- `server/src/app/modules/chatbot/chatbot_engine.py`
- `server/src/app/modules/chatbot/knowledge_base.py`
- `frontend/src/app/features/chatbot/` ChatWidget

## Dependencias
- API de IA externa (procesamiento lenguaje natural)
- knowledge_base para respuestas

## Endpoints
| POST | /api/chatbot/message | Enviar mensaje |
| POST | /api/chatbot/escalate | Escalar a humano |