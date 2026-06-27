# Especificacion: Balanced Scorecard

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-E01 (Consultar Balanced Scorecard), CU-E08 (Generar reporte gerencial consolidado)

## 1. Objetivo

Consultar el Balanced Scorecard organizado en 4 perspectivas (Financiera, Cliente, Procesos Internos, Aprendizaje/Tecnologia) con KPIs y semaforos.

## 2. Contexto

El BSC conecta los objetivos estrategicos con KPIs medibles desde el modelo estrella.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Gerente general | Toma decisiones estrategicas |
| Super Admin | Supervisa KPIs globales |

## 4. KPIs por perspectiva

### Financiera
| KPI | Formula | Meta |
|-----|---------|------|
| Revenue bruto | SUM(price_usd WHERE reserva_bool=true) | +15% por ciclo |
| Precio promedio | AVG(price_usd) | Subir por segmento |

### Cliente
| KPI | Formula | Meta |
|-----|---------|------|
| Tasa de conversion | reservas / eventos x 100 | Mejora trimestral |
| CTR | clicks / eventos x 100 | >30% |
| Rating promedio resenas | AVG(rating) | >4.0 |

### Procesos Internos
| KPI | Formula | Meta |
|-----|---------|------|
| Ejecuciones ETL exitosas | COUNT(status=success) / total | >95% |
| Tiempo promedio ETL | AVG(duration) | <60 min |

### Aprendizaje/Tecnologia
| KPI | Formula | Meta |
|-----|---------|------|
| Cobertura integraciones | endpoints documentados / total | 100% |

## 5. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar BSC con 4 perspectivas y sus KPIs | Alta |
| RF-002 | Cada KPI debe tener indicador visual (semaforo) | Alta |
| RF-003 | El sistema debe mostrar tendencia del KPI | Alta |
| RF-004 | El sistema debe permitir exportar reporte gerencial | Media |

## 6. Escenarios

### Escenario 1: Consultar BSC
```gherkin
Dado que el gerente general consulta el BSC
Cuando ve las 4 perspectivas
Entonces cada perspectiva muestra sus KPIs con semaforo y tendencia
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | BSC muestra 4 perspectivas con KPIs |
| CA-002 | Semaforos se calculan segun metas |
| CA-003 | Exportacion de reporte funciona |

## 8. Dependencias

- Colecciones: fact_hotel_reservations, dim_*, etl_executions, data_quality_reports
