# Especificacion: Tarifas Calendario

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O18 (Configurar tarifas por fecha en calendario de precios), CU-T06 (Validar consistencia de tarifas)

## 1. Objetivo

Configurar tarifas por fecha y plan tarifario en el calendario de precios, permitiendo establecer precios especificos por dia que pueden diferir del base_price del plan.

## 2. Contexto

El calendario de tarifas (hotel_rate_calendar) almacena el precio por noche para cada combinacion de hotel, plan tarifario y fecha. Cada entrada tiene un _id semantico {hotel_id}_{rate_plan_id}_{date}.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Revenue manager | Configura tarifas por fecha y temporada |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar calendario mensual de precios por plan tarifario | Alta |
| RF-002 | El sistema debe permitir editar precio por fecha individual | Alta |
| RF-003 | El sistema debe permitir actualizacion batch por rango de fechas | Alta |
| RF-004 | El sistema debe validar que price > 0 | Alta |
| RF-005 | El sistema debe generar entradas automaticas basadas en base_price + reglas de temporada | Media |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Actualizacion batch (30 dias) menos de 2s |
| RNF-002 | Carga de calendario mensual menos de 1s |

## 6. Reglas de negocio

- El precio por fecha puede diferir del base_price del plan tarifario
- _id semantico: {hotel_id}_{rate_plan_id}_{YYYY-MM-DD}
- Si no hay entrada en el calendario para una fecha, se usa base_price del plan
- Las reglas de temporada se precargan al crear el plan, pero el partner puede sobreescribir

## 7. Entradas

```json
{
  "date": "2026-07-15",
  "price": 180.00
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "_id": "HOTEL001_rp_001_2026-07-15",
    "hotel_id": "HOTEL001",
    "rate_plan_id": "rp_001",
    "date": "2026-07-15",
    "price": 180.00,
    "source": "manual_override"
  }
}
```

## 9. Escenarios

### Escenario 1: Actualizar precio para una fecha especifica
```gherkin
Dado que el partner ve el calendario de julio para el plan rp_001
Cuando actualiza el precio del 15 de julio a 180.00
Entonces el sistema guarda el precio en hotel_rate_calendar
Y el calendario muestra el nuevo precio
```

### Escenario 2: Actualizacion batch mensual
```gherkin
Dado que el partner selecciona un rango de 30 dias para el plan rp_001
Cuando aplica precio 200.00 para fines de semana
Entonces el sistema actualiza solo los sabados y domingos del rango
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Calendario mensual se muestra con precios por dia |
| CA-002 | Precio individual se actualiza correctamente |
| CA-003 | Actualizacion batch funciona para rangos |
| CA-004 | price > 0 se valida |

## 11. Restricciones

- price en USD, positivo, maximo 99999.99
- No se pueden modificar fechas pasadas
- Fechas sin entrada usan base_price del plan

## 12. Dependencias

- Coleccion hotel_rate_calendar
- Modulo partner/services/rates.py
- Depende de: planes tarifarios (spec 019)

## 13. Fuera de alcance

- Precios dinamicos automaticos basados en ocupacion
- Reglas de pricing por anticipacion (booking window)
