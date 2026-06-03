# Matriz de Navegación por Rol

## Resumen

| # | Rol | Sidebar visible | Shell |
|---|-----|----------------|-------|
| 1 | `super_admin` | Gestión + Sistema (todo) | management + system |
| 2 | `admin_sistema` | Gestión + Sistema (todo) | management + system |
| 3 | `hotel_partner` | Gestión (operativo + propiedad + reportes) | management |
| 4 | `gerente_hotel` | Gestión (operativo limitado + habitaciones + políticas + reportes) | management |
| 5 | `revenue_manager` | Gestión (disponibilidad + tarifas + propiedades + reportes) | management |
| 6 | `marketing_hotelero` | Gestión (propiedades + políticas + amenities + reportes) | management |
| 7 | `operador_datos` | Gestión (reportes) + Sistema (monitoreo + auditoría) | management + system |
| 8 | `auditor_datos` | Gestión (reportes) + Sistema (auditoría + monitoreo) | management + system |
| 9 | `cliente` | N/A (Top Nav: buscar, reservas, perfil) | account + public |

## Matriz detallada

### Gestión — `/management/*`

| Ruta | super_admin | admin_sistema | hotel_partner | gerente_hotel | revenue_manager | marketing_hotelero | operador_datos | auditor_datos | cliente |
|------|:-----------:|:-------------:|:-------------:|:-------------:|:---------------:|:------------------:|:--------------:|:-------------:|:-------:|
| Panel hotelero `/management` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reservas `/management/reservations` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Disponibilidad `/management/availability` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Check-ins `/management/check-ins` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Check-outs `/management/check-outs` | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Propiedades `/management/properties` | ✅ | ✅ | ✅ | ❌¹ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Habitaciones `/management/rooms` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌² | ❌ | ❌ | ❌ |
| Tarifas `/management/rates` | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Políticas `/management/policies` | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Amenities `/management/amenities` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Reportes `/management/reports` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Configuración `/management/settings` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

¹ *gerente_hotel*: puede acceder por URL directa a propiedades individuales desde Habitaciones, pero el módulo Propiedades no aparece en el sidebar. Solo lectura si accede.

² *marketing_hotelero*: Habitaciones no aparece en sidebar. Puede acceder por URL directa desde Propiedades si el backend lo permite, pero solo lectura.

### Sistema — `/system/*`

| Ruta | super_admin | admin_sistema | hotel_partner | gerente_hotel | revenue_manager | marketing_hotelero | operador_datos | auditor_datos | cliente |
|------|:-----------:|:-------------:|:-------------:|:-------------:|:---------------:|:------------------:|:--------------:|:-------------:|:-------:|
| Usuarios `/system/users` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Permisos `/system/permissions` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Auditoría `/system/audit` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ |
| Monitoreo `/system/monitoring` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅¹ | ❌ |

¹ *auditor_datos*: solo lectura — las acciones POST (ejecutar ETL, limpiar evidencia) están bloqueadas por el backend (`etl.execute` no asignado a `auditor_datos`).

### Público / Cliente

| Ruta | super_admin | admin_sistema | hotel_partner | gerente_hotel | revenue_manager | marketing_hotelero | operador_datos | auditor_datos | cliente |
|------|:-----------:|:-------------:|:-------------:|:-------------:|:---------------:|:------------------:|:--------------:|:-------------:|:-------:|
| Buscar hoteles `/search` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hotel destacado `/hotels/:id` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mis reservas `/account/bookings` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Perfil `/account/profile` | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

## Notas de solo lectura

| Rol | Restricción | Mecanismo |
|-----|-------------|-----------|
| `auditor_datos` | No puede ejecutar ETL, no puede modificar usuarios/permisos, ni escribir en módulos de gestión. | Backend `route_permissions.py` sin permisos de escritura (`etl.execute`, `users.manage`, etc.) |
| `marketing_hotelero` | Habitaciones y contenido de propiedades son solo lectura. | Backend: no tiene `hotels.manage` sobre escritura de habitaciones. |
| `gerente_hotel` | Propiedades no aparece en sidebar pero puede acceder por URL directa desde Habitaciones. Solo lectura. | No hay ruta POST/PUT/DELETE expuesta para `gerente_hotel` en propiedades. |
| `revenue_manager` | Reservas visible, pero sin acciones de check-in/check-out ni cancelación. | Backend: no tiene roles operativos. |

## Rutas sin sidebar pero accesibles por URL

Estas rutas existen y funcionan por navegación directa, pero no tienen entrada en el sidebar:

- `/management/check-ins` — solo accesible por `super_admin`, `admin_sistema`, `gerente_hotel` (sidebar) y por URL directa si el roleGuard lo permite.
- `/management/check-outs` — igual que check-ins.
- `/management/properties/:id` — detalle de propiedad, accesible desde la tabla de propiedades.

## Archivos de código involucrados

| Archivo | Propósito |
|---------|-----------|
| `frontend/src/app/app.routes.ts` | Guards de shell (management, system, account) |
| `frontend/src/app/shared/ui/sidebar-nav/sidebar-nav.ts` | Sidebar con filtrado por `allowedRoles` en ítems |
| `frontend/src/app/shared/ui/access-nav/access-nav.ts` | Top nav con mismos filtros (glass-morphism) |
| `frontend/src/app/shared/ui/top-nav/top-nav.ts` | Top nav público (cliente y no autenticado) |
| `frontend/src/app/core/auth/auth.guard.ts` | `authGuard` + `roleGuard` usados en rutas |
| `frontend/src/app/features/system-admin/system-admin.routes.ts` | Guards individuales por ruta del sistema |
| `src/app/security/route_permissions.py` | Backend: reglas de acceso por rol y permiso |
