# Especificacion: Reportes de Calidad de Datos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O27 (Consultar reporte de calidad y registros rechazados), CU-E07 (Evaluar calidad de datos, pipeline Airflow)

## 1. Objetivo

Consultar reportes de calidad de datos generados por cada ejecucion ETL, incluyendo registros procesados, rechazados y completitud.

## 2. Contexto

Cada ejecucion ETL produce un reporte de calidad en data_quality_reports. Los rechazos van a rejected_records con razon exacta.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Auditor de Datos | Revisa calidad y registros rechazados |
| Operador de datos | Monitorea ejecuciones ETL |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar lista de ejecuciones ETL con fecha, estado, duracion | Alta |
| RF-002 | El sistema debe mostrar detalle de calidad por ejecucion | Alta |
| RF-003 | El sistema debe listar registros rechazados con razon y raw_record | Alta |
| RF-004 | El sistema debe mostrar completitud por columna (% de nulls) | Alta |
| RF-005 | El sistema debe permitir exportar reporte a PDF/CSV | Media |

## 5. Reglas de negocio

- Cada ejecucion ETL produce exactamente un reporte de calidad
- Los registros rechazados incluyen raw_record completo y rejection_reason
- Las ejecuciones se registran en etl_executions

## 6. Escenarios

### Escenario 1: Consultar reporte de calidad
```gherkin
Dado que el auditor consulta la lista de ejecuciones
Cuando selecciona una ejecucion especifica
Entonces ve el detalle con total, aceptados, rechazados
Y la completitud por columna
```

## 7. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Lista de ejecuciones se muestra correctamente |
| CA-002 | Detalle de calidad por ejecucion funciona |
| CA-003 | Registros rechazados se listan con razon |
| CA-004 | Exportacion a PDF/CSV funciona |

## 8. Dependencias

- Coleccion etl_executions
- Coleccion data_quality_reports
- Coleccion rejected_records
- Modulo src/etl/validate.py

## 9. Fuera de alcance

- Alertas automaticas cuando la calidad baja de un umbral
- ML para deteccion de anomalias en calidad
