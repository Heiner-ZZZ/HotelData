# Especificacion: Estrategia de Revenue

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E06 (Definir estrategia de revenue, campanas, pricing y proyeccion de demanda)

## 1. Objetivo

Definir estrategia de revenue, campanas y pricing mediante forecasting y analisis de promociones.

## 2. Actores

| Actor | Descripcion |
|-------|-------------|
| Revenue manager | Define estrategia de precios y promociones |

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar tendencias de precio promedio por destino y temporada | Alta |
| RF-002 | El sistema debe mostrar efectividad de promociones | Alta |
| RF-003 | El sistema debe permitir proyectar demanda | Media |
| RF-004 | El sistema debe mostrar revenue por canal y segmento | Alta |

## 4. Escenarios

### Escenario 1: Analizar efectividad de promociones
```gherkin
Dado que el revenue manager consulta efectividad
Cuando compara revenue con promocion vs sin promocion
Entonces ve la diferencia en conversion
```

## 5. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Tendencias de precio se muestran correctamente |
| CA-002 | Efectividad de promociones se compara correctamente |
| CA-003 | Proyeccion de demanda usa datos historicos |

## 6. Dependencias

- Colecciones: fact_hotel_reservations, dim_promotions, dim_dates
