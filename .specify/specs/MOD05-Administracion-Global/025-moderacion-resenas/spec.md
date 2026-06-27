# Especificacion: Moderacion de Resenas

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O23 (Moderar y responder resena), CU-T13 (Gestionar resenas, reputacion online y respuestas)

## 1. Objetivo

Permitir que marketing o super admin modere las resenas de huespedes (aprobar/rechazar) y que el hotel partner responda a resenas aprobadas.

## 2. Contexto

Las resenas pasan por un flujo de moderacion antes de ser publicas. Esto permite filtrar contenido inapropiado, spam o resenas fraudulentas.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Marketing hotelero | Modera y responde resenas |
| Super Admin | Moderacion general del sistema |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar resenas pendientes de moderacion | Alta |
| RF-002 | El sistema debe permitir aprobar resena | Alta |
| RF-003 | El sistema debe permitir rechazar resena | Alta |
| RF-004 | El sistema debe permitir responder a resena aprobada | Alta |
| RF-005 | El sistema debe validar que solo marketing/super admin pueden moderar | Alta |
| RF-006 | El sistema debe validar que solo hotel_partner del hotel puede responder | Alta |

## 5. Reglas de negocio

- Solo marketing_hotelero y super_admin pueden moderar
- Solo hotel_partner del hotel puede responder
- No se puede responder una resena rechazada
- Las resenas aprobadas son visibles en el detalle del hotel
- Una vez aprobada o rechazada, no se puede cambiar

## 6. Entradas (moderacion)

```json
{
  "action": "approve",
  "moderation_note": "Resena verificada, cliente confirmado"
}
```

## 7. Salidas

```json
{
  "success": true,
  "data": {
    "review_id": "rev_001",
    "moderation_status": "approved",
    "moderated_by": "user_admin",
    "moderated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 8. Escenarios

### Escenario 1: Moderar resena
```gherkin
Dado que marketing ve una resena pendiente
Cuando la aprueba
Entonces el sistema cambia moderation_status a approved
Y la resena se vuelve visible en el hotel
```

### Escenario 2: Rechazar resena
```gherkin
Dado que marketing ve una resena con contenido inapropiado
Cuando la rechaza
Entonces el sistema cambia moderation_status a rejected
Y la resena no se muestra publicamente
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Moderacion (aprobar/rechazar) funciona correctamente |
| CA-002 | Solo usuarios autorizados pueden moderar |
| CA-003 | Respuesta se guarda solo en resenas aprobadas |

## 10. Dependencias

- Coleccion reviews
- Modulo modules/reviews/services/reviews.py
- Depende de: registro de resenas (spec 024)

## 11. Fuera de alcance

- Moderacion automatica con IA
- Apelacion de resena rechazada por el cliente
