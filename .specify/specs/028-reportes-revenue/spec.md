# Especificacion: Reportes de Revenue

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O26 (Consultar reportes de revenue y mercado), CU-E02 (Analizar conversion digital y CAC), CU-E05 (Analizar mercados visitantes), CU-E06 (Definir estrategia de revenue)

## 1. Objetivo

Consultar reportes y dashboards de revenue, conversion, mercados, top hoteles/destinos/paises basados en el modelo estrella.

## 2. Contexto

El modelo estrella almacena datos de busqueda y reserva en fact_hotel_reservations con 12 dimensiones. Los reportes agregan estos datos para mostrar KPIs.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente de hotel | Consulta reportes operativos |
| Revenue manager | Analiza revenue y conversion |
| Marketing hotelero | Analiza mercados y campanas |
| Auditor de datos | Consulta calidad y tendencias |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar dashboard con eventos totales, reservas, clicks, revenue, precio promedio | Alta |
| RF-002 | El sistema debe mostrar top hoteles por revenue | Alta |
| RF-003 | El sistema debe mostrar top destinos por demanda | Alta |
| RF-004 | El sistema debe mostrar top paises visitantes por eventos | Alta |
| RF-005 | El sistema debe permitir filtrar por periodo (dia, semana, mes, trimestre) | Alta |
| RF-006 | El sistema debe calcular tasa de conversion y CTR | Alta |

## 5. Reglas de negocio

- Los KPIs se calculan agregando fact_hotel_reservations con $lookup a dimensiones
- Booking Conversion Rate = reservas / eventos x 100
- CTR = clicks / eventos x 100
- Los datos son de solo lectura

## 6. Entradas

GET /api/reports/revenue/summary?period=month&from=2026-01-01&to=2026-06-22

## 7. Salidas

```json
{
  "data": {
    "total_events": 150000,
    "total_clicks": 45000,
    "total_bookings": 12000,
    "total_revenue": 1800000.00,
    "avg_price": 150.00,
    "conversion_rate": 8.0,
    "ctr": 30.0,
    "top_hotels": [{ "prop_id": "HOTEL001", "revenue": 250000 }]
  }
}
```

## 8. Escenarios

### Escenario 1: Consultar dashboard de revenue
```gherkin
Dado que el revenue manager esta autenticado
Cuando consulta el dashboard de revenue mensual
Entonces ve eventos, reservas, conversion, revenue y precio promedio
Y puede ver top hoteles, destinos y paises
```

## 9. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Dashboard muestra KPIs correctos del modelo estrella |
| CA-002 | Filtros por periodo funcionan |
| CA-003 | Top hoteles/destinos/paises se muestran correctamente |

## 10. Dependencias

- Coleccion fact_hotel_reservations
- Dimensiones: dim_hotels, dim_destinations, dim_visitor_countries, dim_dates

## 11. Fuera de alcance

- Forecasting predictivo con ML
- Dashboard en tiempo real (streaming)
