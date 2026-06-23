# Especificacion: Historial de Cambios

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O13 (Consultar historial de cambios de propiedad), CU-T10 (Auditar cambios y actividad del sistema)

## 1. Objetivo

Consultar el historial de cambios de la propiedad (perfil y contenido) con filtros por fecha, campo y usuario, para fines de auditoria y trazabilidad.

## 2. Contexto

Cada cambio en el perfil de la propiedad (hotel_profile_changes) o en el contenido (hotel_content_changes) se registra automaticamente. Este spec permite consultar ese historial de forma filtrada y paginada.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Auditor de Datos | Revisa trazabilidad de cambios de perfil y contenido |
| Hotel partner | Consulta cambios de sus propias propiedades |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe listar cambios por propiedad con paginacion | Alta |
| RF-002 | El sistema debe permitir filtrar por rango de fechas | Alta |
| RF-003 | El sistema debe permitir filtrar por campo modificado | Media |
| RF-004 | El sistema debe permitir filtrar por usuario que realizo el cambio | Media |
| RF-005 | El sistema debe mostrar old_value y new_value por campo | Alta |
| RF-006 | El sistema debe mostrar quien realizo el cambio y cuando | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La consulta debe responder en menos de 1s con indices adecuados |
| RNF-002 | El historial debe conservarse indefinidamente |

## 6. Reglas de negocio

- Los datos son inmutables (solo lectura, no se pueden modificar ni eliminar registros de auditoria)
- El historial incluye cambios de perfil (hotel_profile_changes) y contenido (hotel_content_changes)
- Los registros se ordenan por changed_at descendente (mas reciente primero)

## 7. Entradas

GET /api/management/properties/{id}/history?from=2026-01-01&to=2026-06-22&field=nombre_comercial&user=user_abc&page=1&per_page=20

## 8. Salidas

```json
{
  "data": [
    {
      "id": "change_001",
      "field": "nombre_comercial",
      "old_value": "Hotel Vista Hermosa",
      "new_value": "Hotel Vista Hermosa Premium",
      "changed_by": "user_abc123",
      "changed_by_name": "Carlos Lopez",
      "changed_at": "2026-06-22T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 45,
    "pages": 3
  }
}
```

## 9. Escenarios

### Escenario 1: Consultar historial con filtros
```gherkin
Dado que el hotel partner esta autenticado
Y tiene asignada la propiedad HOTEL001
Cuando consulta GET /api/management/properties/HOTEL001/history?from=2026-01-01&field=nombre_comercial
Entonces el sistema responde 200
Y la respuesta incluye solo cambios del campo nombre_comercial
Y los resultados estan paginados
```

### Escenario 2: Consultar detalle de un cambio especifico
```gherkin
Dado que existe un cambio con ID change_001 en HOTEL001
Cuando el partner consulta GET /api/management/properties/HOTEL001/history/change_001
Entonces el sistema responde 200
Y la respuesta incluye old_value, new_value, changed_by y changed_at
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | La lista paginada funciona correctamente |
| CA-002 | Los filtros por fecha reducen correctamente los resultados |
| CA-003 | Los filtros por campo funcionan correctamente |
| CA-004 | El detalle de cambio muestra old/new value correctamente |

## 11. Restricciones

- Solo se puede consultar historial de propiedades a las que se tiene acceso
- No se pueden modificar ni eliminar registros de auditoria

## 12. Dependencias

- Coleccion hotel_profile_changes (lectura)
- Coleccion hotel_content_changes (lectura)
- Indice compuesto: { hotel_id: 1, changed_at: -1 }
- Indice compuesto: { hotel_id: 1, field: 1, changed_at: -1 }

## 13. Fuera de alcance

- Exportacion del historial a CSV/PDF
- Auditoria de actividad de usuarios (sesiones, logins)
