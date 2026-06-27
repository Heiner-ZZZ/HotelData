# Especificación: Gestionar Campañas Promocionales Multicanal

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-O34

## 1. Objetivo
Lanzar campañas promocionales segmentadas a través de múltiples canales (email, SMS, push) dirigidas a huéspedes según criterios de segmentación (historial, destino, temporada, valor), midiendo efectividad.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Marketing hotelero | Crea y lanza campañas |
| Revenue manager | Define promociones asociadas |

## 3. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Crear campaña con nombre, segmento, canales, promoción asociada |
| RF-002 | Segmentar huéspedes por frecuencia, destino, valor, recencia |
| RF-003 | Programar envío inmediato o diferido |
| RF-004 | Medir efectividad: apertura, CTR, conversión, revenue |
| RF-005 | Cancelar campaña programada |

## 4. Reglas de negocio
- Máximo 5 campañas promocionales por huésped por semana
- Segmento se calcula al momento del envío
- Huéspedes deben tener opt-in promocional

## 5. Colecciones
marketing_campaigns, campaign_segments, notification_templates, notification_logs, promotion_campaigns