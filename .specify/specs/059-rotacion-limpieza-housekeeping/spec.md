# Especificación: Gestionar Rotación y Limpieza de Habitaciones (Táctico)

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-T14

## 1. Objetivo
Optimizar tiempo de rotación entre check-out y check-in, estableciendo métricas objetivo de eficiencia de limpieza, asignación de personal y reducción de tiempos muertos.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Gerente de hotel | Define objetivos y asigna personal |

## 3. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Definir tiempo objetivo de rotación por hotel |
| RF-002 | Asignar personal de limpieza por turno |
| RF-003 | Medir tiempo de rotación real vs objetivo |
| RF-004 | Dashboard de eficiencia de limpieza |

## 4. Reglas de negocio
- Tiempo de rotación se mide desde check-out hasta room_status cambiado a "disponible"
- Alertas cuando se supera tiempo objetivo

## 5. Colecciones
room_status_log, housekeeping_tasks, hotel_settings