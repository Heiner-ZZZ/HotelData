# Arquitectura modular para integraciones GA03

## Objetivo

Preparar HotelData Hub Analytics para nuevas funcionalidades de reservas hoteleras sin migrar de framework, sin crear carpetas separadas `backend/frontend` y sin romper las rutas actuales.

El proyecto mantiene FastAPI + Jinja2 + MongoDB.

## Por qué se separa por módulos

La separación por módulos permite que cada área funcional crezca con sus propias rutas, servicios y esquemas sin mezclar responsabilidades. Esto facilita incorporar nuevas capacidades de forma progresiva:

- Autenticación y usuarios.
- Catálogo hotelero.
- Reservas.
- Partner Central.
- Tarifas, promociones y revenue.
- Auditoría ampliada.

La estructura nueva no reemplaza `src/app/features`. La complementa como espacio para funcionalidades futuras de negocio.

## Estructura creada

```text
src/app/modules/
  auth/
    __init__.py
    routes.py
    service.py
    schemas.py
  users/
    __init__.py
    routes.py
    service.py
    schemas.py
  hotels/
    __init__.py
    routes.py
    service.py
    schemas.py
  reservations/
    __init__.py
    routes.py
    service.py
    schemas.py
  partner/
    __init__.py
    routes.py
    service.py
    schemas.py
  revenue/
    __init__.py
    routes.py
    service.py
    schemas.py
  audit/
    __init__.py
    routes.py
    service.py
    schemas.py
```

## Módulos activos

Los módulos actuales activos siguen estando en `src/app/features`:

- Dashboard y consulta de datos.
- Registros.
- Calidad.
- Colecciones.
- Catálogos.
- Auditoría actual.
- CRUD TA02/GA03.
- Centro de control ETL `/etl-status`.

Rutas actuales conservadas:

- `/ta02`
- `/ta02/crud`
- `/etl-status`

## Módulos en preparación

Los módulos nuevos en `src/app/modules` quedan preparados con rutas de estado bajo `/modules/<modulo>/status`:

- `/modules/auth/status`
- `/modules/users/status`
- `/modules/hotels/status`
- `/modules/reservations/status`
- `/modules/partner/status`
- `/modules/revenue/status`
- `/modules/audit/status`

Estas rutas no implementan login real, reservas reales, pagos, tarifas operativas ni partner central. Solo documentan y exponen el estado del módulo como preparación.

## Compatibilidad con TA02/GA03

La compatibilidad se conserva porque:

- No se borran rutas anteriores.
- No se cambia el framework.
- No se mueve el ETL.
- No se modifica Airflow.
- No se modifica PocketBase.
- No se modifica MongoDB.
- No se modifica la estructura de templates Jinja2 existente.
- Los módulos nuevos usan prefijos propios y no colisionan con `/ta02`, `/ta02/crud` ni `/etl-status`.

## Relación con la visión GA03

GA03 documenta 32 casos de uso en 8 paquetes. La nueva estructura modular sirve como base para implementar progresivamente esos paquetes:

| Módulo | Paquetes relacionados | Estado |
| --- | --- | --- |
| `auth` | Cuenta, sesión y perfil de usuario | Preparación |
| `users` | Administración de usuarios, roles y permisos | Preparación |
| `hotels` | Experiencia hotelera y contenido de hotel | Preparación |
| `reservations` | Core de reservas hoteleras | Preparación |
| `partner` | Gestión hotelera / Partner Central | Preparación |
| `revenue` | Tarifas, promociones y revenue | Preparación |
| `audit` | Auditoría y gobierno ampliado | Preparación |

## Regla de evolución

Toda nueva funcionalidad debe agregarse dentro del módulo correspondiente y conectarse a la aplicación solo cuando no rompa las rutas validadas de TA02/GA03.
