# Especificación: Gestionar Up-Selling y Ancillaries

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-O36

## 1. Objetivo
Ofrecer y gestionar servicios adicionales durante la estancia: upgrade de habitación, late check-out, early check-in, spa, cenas, traslados, generando ingresos adicionales.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Recepcionista | Ofrece servicios durante check-in/out |
| Revenue manager | Define precios y estrategias |

## 3. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Mostrar oportunidades de up-selling basadas en disponibilidad y perfil |
| RF-002 | Registrar cargo adicional en additional_charges |
| RF-003 | Actualizar booking_orders.total al agregar ancillary |
| RF-004 | Para upgrades: actualizar room_type asignado |
| RF-005 | Registrar en upselling_log para analítica |

## 4. Reglas de negocio
- Máximo 2 ofertas por interacción
- Late check-out máx 20:00hs
- Upgrade solo si hay disponibilidad en categoría superior

## 5. Colecciones
additional_charges, booking_orders, upselling_log