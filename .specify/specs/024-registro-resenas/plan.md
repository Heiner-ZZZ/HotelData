# Plan de Implementación: Registro de Reseñas

**Branch**: `024-registro-resenas` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Cliente (post-estancia)
  → ReviewForm (rating 1-5, título, comentario)
    → POST /api/reviews
      → services/reviews.py
        → reviews collection (moderation_status: "pending")
        → fact_reviews (dual-write)
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| POST | /api/reviews | Crear reseña (post-estancia) |
| GET | /api/hotels/{id}/reviews | Obtener reseñas aprobadas de un hotel (top 5) |
| GET | /api/reviews/{id} | Obtener detalle de reseña |

## Reglas de negocio

- Solo huéspedes con estancia completada pueden reseñar
- Una reseña por reserva (unique booking_id)
- Rating obligatorio (1-5), comentario opcional
- Dual-write a fact_reviews para analítica
- Moderation_status inicial: "pending"
