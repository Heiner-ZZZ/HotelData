# Especificacion: Politicas Hoteleras

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O20 (Gestionar politicas hoteleras), CU-T07 (Validar consistencia de politicas y contenido)

## 1. Objetivo

Gestionar las politicas del hotel: horarios de check-in/out, politica de cancelacion, mascotas, ninos y restricciones de estancia.

## 2. Contexto

Cada propiedad hotelera tiene politicas que definen las reglas de operacion. Se almacenan en hotel_policies y los cambios se registran en hotel_content_changes.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Hotel partner | Configura politicas de su propiedad |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir configurar horario de check-in y check-out | Alta |
| RF-002 | El sistema debe permitir configurar politica de cancelacion (horas antes) | Alta |
| RF-003 | El sistema debe permitir indicar si se admiten mascotas y costo | Alta |
| RF-004 | El sistema debe permitir indicar politica de ninos y cargo por cama extra | Alta |
| RF-005 | El sistema debe permitir configurar estancia minima y maxima | Alta |
| RF-006 | El sistema debe validar que check-out > check-in | Alta |
| RF-007 | El sistema debe registrar cambios en hotel_content_changes | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Actualizacion de politicas menos de 500ms |
| RNF-002 | Las politicas deben ser accesibles sin autenticacion (lectura publica) |

## 6. Reglas de negocio

- check_out_time debe ser despues de check_in_time
- cancellation_hours define horas antes del check-in para cancelacion gratuita
- min_stay y max_stay en noches minimas/maximas
- Los cambios se registran en hotel_content_changes para trazabilidad

## 7. Entradas

```json
{
  "check_in_time": "15:00",
  "check_out_time": "12:00",
  "cancellation_hours": 48,
  "pets_allowed": true,
  "pet_fee": 25.00,
  "children_allowed": true,
  "extra_bed_fee": 30.00,
  "min_stay": 1,
  "max_stay": 30
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "hotel_id": "HOTEL001",
    "check_in_time": "15:00",
    "check_out_time": "12:00",
    "cancellation_hours": 48,
    "pets_allowed": true,
    "pet_fee": 25.00,
    "updated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Configurar politicas exitosamente
```gherkin
Dado que el partner esta en la pagina de politicas
Cuando completa el formulario con horarios y cargos
Entonces el sistema guarda las politicas en hotel_policies
Y registra el cambio en hotel_content_changes
```

### Escenario 2: Check-out antes que check-in
```gherkin
Dado que el partner ingresa check_in=15:00 y check_out=14:00
Cuando intenta guardar
Entonces el sistema responde 400 Bad Request
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Politicas se guardan correctamente |
| CA-002 | Check-out > check-in se valida |
| CA-003 | Politicas son accesibles sin autenticacion (lectura) |
| CA-004 | Cambios quedan registrados en hotel_content_changes |

## 11. Restricciones

- check_in_time y check_out_time en formato HH:MM
- cancellation_hours entero positivo, maximo 720 (30 dias)
- min_stay mayor o igual a 1, max_stay mayor o igual a min_stay, maximo 365

## 12. Dependencias

- Coleccion hotel_policies
- Coleccion hotel_content_changes (auditoria)
- Modulo partner/services/content/save.py

## 13. Fuera de alcance

- Politicas diferenciadas por temporada
- Politicas de cancelacion no reembolsable vs reembolsable
