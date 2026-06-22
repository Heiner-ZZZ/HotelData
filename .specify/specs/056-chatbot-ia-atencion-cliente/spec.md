# Especificación: Atender Cliente Mediante Asistente Virtual (Chatbot IA)

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-O35

## 1. Objetivo
Proporcionar asistente virtual conversacional (chatbot IA) que atienda consultas sobre hoteles, reservas, check-in/out, servicios y FAQs, con capacidad de escalar a agente humano.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Cliente | Inicia conversación desde widget de chat |
| Recepcionista | Recibe conversaciones escaladas |

## 3. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Chatbot responde consultas en lenguaje natural |
| RF-002 | Chatbot puede hacer reservas simples si cliente autenticado |
| RF-003 | Chatbot escala a humano si no puede resolver |
| RF-004 | Conversaciones quedan registradas para análisis |
| RF-005 | Base de conocimiento configurable |

## 4. Reglas de negocio
- Chatbot debe presentarse como asistente virtual
- Datos sensibles (tarjetas) no deben procesarse
- Historial almacenado 90 días

## 5. Colecciones
chatbot_knowledge_base, chatbot_conversations, booking_orders