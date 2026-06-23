# Especificacion: Frontend - Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O22, CU-O23 (Registro y moderacion de resenas)

## 1. Objetivo

UI de resenas: listado, detalle, moderacion, respuesta del hotel.

## 2. Componentes

| Componente | Ruta | CU asociado |
|------------|------|-------------|
| ReviewForm | /reviews/new | CU-O22 |
| ReviewListPage | /reviews | CU-O22 |
| ModeratePage | /reviews/moderate | CU-O23 |
| ReviewDetailPage | /reviews/:id | CU-O23 |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | ReviewForm con rating 1-5, titulo, comentario | Alta |
| RF-002 | ReviewListPage visible en detalle de hotel | Alta |
| RF-003 | ModeratePage con tabla de resenas pendientes | Alta |
| RF-004 | Botones de aprobar/rechazar con confirmacion | Alta |
| RF-005 | Formulario de respuesta del hotel en resena aprobada | Alta |

## 4. Dependencias

- frontend/src/app/features/reviews/
- modules/reviews/routes.py
