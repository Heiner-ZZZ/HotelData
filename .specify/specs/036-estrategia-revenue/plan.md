# Plan de Implementación: Estrategia de Revenue

**Branch**: `036-estrategia-revenue` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Revenue Manager
  → EstrategiaRevenuePage
    → GET /api/reports/revenue/trends (tendencias precio)
    → GET /api/reports/revenue/promotions (efectividad)
    → GET /api/reports/revenue/forecast (proyección)
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/reports/revenue/trends | Tendencias de precio por destino/temporada |
| GET | /api/reports/revenue/promotions | Efectividad (con/sin promoción) |
| GET | /api/reports/revenue/forecast | Proyección de demanda (histórico) |
| GET | /api/reports/revenue/by-channel | Revenue por canal y segmento |

## Fuentes

- `fact_hotel_reservations` con filtro `reserva_bool=true`
- Dimensiones para segmentación
- Histórico de promociones para comparativa
