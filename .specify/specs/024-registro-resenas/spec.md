# Especificacion: Registro de Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O22 (Registrar resena de estancia), CU-T13 (Gestionar resenas)

## 1. Objetivo

Permitir que los huespedes registren resenas de su estancia con calificacion (1-5), titulo y comentario, con dual-write a fact_reviews para analitica.

## 2. Contexto

Solo huespedes con estancia completada pueden resenar. Una resena por reserva. Las resenas pasan por moderacion (spec 025) antes de ser publicas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Cliente | Registra resena post-estancia |
| Sistema | Valida elegibilidad y escribe dual-write |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir crear resena con rating, titulo y comentario | Alta |
| RF-002 | El sistema debe validar que solo huespedes post-estancia pueden resenar | Alta |
| RF-003 | El sistema debe validar una resena por reserva (unique booking_id) | Alta |
| RF-004 | El sistema debe asignar moderation_status = pending inicial | Alta |
| RF-005 | El sistema debe hacer dual-write a fact_reviews | Alta |
| RF-006 | El sistema debe mostrar top 5 resenas aprobadas en detalle del hotel | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Creacion de resena menos de 500ms incluyendo dual-write |
| RNF-002 | Carga de resenas en detalle del hotel menos de 300ms |

## 6. Reglas de negocio

- Solo huespedes con estancia completada pueden resenar (booking status = checked_out)
- Una resena por reserva (unique booking_id)
- Rating obligatorio (1-5), titulo y comentario opcionales
- Dual-write obligatorio a fact_reviews para analitica

## 7. Entradas

```json
{
  "booking_id": "BK-2026-001",
  "rating": 4,
  "title": "Excelente estancia",
  "comment": "Muy buen hotel, el personal fue atento.",
  "categories": { "cleanliness": 5, "location": 4, "service": 5 }
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "review_id": "rev_001",
    "booking_id": "BK-2026-001",
    "rating": 4,
    "moderation_status": "pending",
    "created_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Registrar resena exitosamente
```gherkin
Dado que el huesped tiene una estancia completada en HOTEL001
Cuando envia POST /api/reviews con rating y comentario
Entonces el sistema responde 201
Y la resena queda en estado pending
Y se escribe en fact_reviews
```

### Escenario 2: Resena duplicada
```gherkin
Dado que ya existe una resena para la reserva BK-2026-001
Cuando el huesped intenta crear otra resena para la misma reserva
Entonces el sistema responde 409 Conflict
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Resena se crea con rating obligatorio |
| CA-002 | Una resena por booking_id |
| CA-003 | Dual-write a fact_reviews funciona |
| CA-004 | moderation_status inicia como pending |

## 11. Restricciones

- Rating: entero 1-5
- Titulo: maximo 200 caracteres
- Comentario: maximo 5000 caracteres

## 12. Dependencias

- Coleccion reviews
- Coleccion fact_reviews (dual-write)
- Modulo modules/reviews/services/reviews.py
- Verificacion de estatus de booking en booking_orders

## 13. Fuera de alcance

- Moderacion automatica con IA
- Notificaciones al hotel cuando recibe resena
