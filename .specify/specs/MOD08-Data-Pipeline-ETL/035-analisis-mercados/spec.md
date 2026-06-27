# Especificacion: Analisis de Mercados

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E05 (Analizar mercados visitantes, destinos, canales y hoteles con mayor rendimiento)

## 1. Objetivo

Analizar mercados visitantes, destinos, canales y hoteles con mayor rendimiento usando las dimensiones del modelo estrella.

## 2. Contexto

Las dimensiones permiten segmentar por pais visitante, destino, canal y propiedad.

## 3. KPIs por dimension

| Dimension | KPI | Formula |
|-----------|-----|---------|
| dim_visitor_countries | Top paises por eventos | COUNT(eventos) GROUP BY pais |
| dim_visitor_countries | Conversion por pais | reservas / eventos x 100 |
| dim_destinations | Top destinos por demanda | COUNT(busquedas) GROUP BY destino |
| dim_sites | Distribucion por canal | COUNT(eventos) GROUP BY site_name |
| dim_hotels | Hoteles con mayor revenue | SUM(price_usd) GROUP BY prop_id |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar top paises por eventos y conversion | Alta |
| RF-002 | El sistema debe mostrar top destinos por demanda y revenue | Alta |
| RF-003 | El sistema debe mostrar distribucion por canal | Alta |
| RF-004 | El sistema debe mostrar hoteles con mayor rendimiento | Alta |

## 5. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Top paises se muestra con eventos y conversion |
| CA-002 | Top destinos con demanda y revenue |
| CA-003 | Distribucion por canal correcta |

## 6. Dependencias

- Colecciones: fact_hotel_reservations, dim_visitor_countries, dim_destinations, dim_sites, dim_hotels
