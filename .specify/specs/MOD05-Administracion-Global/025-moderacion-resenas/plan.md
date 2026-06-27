# Plan de Implementación: Moderación de Reseñas

**Branch**: `025-moderacion-resenas` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Marketing / Super Admin
  → ModeratePage (lista reseñas pendientes)
    → POST /api/reviews/{id}/approve
    → POST /api/reviews/{id}/reject
      → services/reviews.py
        → reviews.moderation_status: "approved" | "rejected"
        → user_activity_logs

Hotel Partner (respuesta)
  → POST /api/reviews/{id}/respond
    → reviews.staff_response: { text, responded_by, responded_at }
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reviews/moderate | Listar reseñas pendientes (admin) |
| POST | /api/reviews/{id}/approve | Aprobar reseña |
| POST | /api/reviews/{id}/reject | Rechazar reseña (con motivo opcional) |
| POST | /api/reviews/{id}/respond | Responder a reseña aprobada |

## Reglas de negocio

- Solo marketing_hotelero y super_admin pueden moderar
- Solo hotel_partner del hotel puede responder
- No se puede responder una reseña rechazada
- Las reseñas aprobadas son visibles en el detalle del hotel
