# Especificación: Monitorear Eficiencia Operativa del Hotel (Estratégico)

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-E09

## 1. Objetivo
Monitorear KPIs operativos del hotel en dashboard ejecutivo: tiempo de rotación, cumplimiento de limpieza, cumplimiento de mantenimiento, ocupación real vs disponible, cargos adicionales promedio.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Gerente general | Visualiza dashboard |
| Super Admin | Supervisa operación general |

## 3. KPIs
| KPI | Fórmula |
|-----|---------|
| Tiempo rotación promedio | AVG(check_out → room_available) |
| Cumplimiento limpieza | tareas_completadas / tareas_asignadas |
| Cumplimiento mantenimiento | mantenimientos_completados / programados |
| Ocupación real | habitaciones_ocupadas / total_habitaciones |

## 4. Colecciones
room_status_log, housekeeping_tasks, maintenance_schedule, booking_orders