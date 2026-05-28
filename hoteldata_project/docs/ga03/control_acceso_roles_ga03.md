# Control de acceso por rol GA03

GA03 implementa login como entrada principal y menú lateral filtrado por rol.

## Flujo de entrada

- `GET /` redirige a `/auth/login` si no existe sesión activa.
- Después del login, cada usuario se envía a su inicio operativo según `primary_role`.
- Si el login recibe `next`, se respeta solo si es una ruta interna segura.

## Menú por rol

El menú se construye desde `src/app/security/navigation.py`.

- `super_admin` y `admin_sistema`: seguridad, usuarios, dashboard, CRUD, ETL y Redis.
- `operador_datos`: ETL, dashboard y auditoría operativa.
- `auditor_datos`: analytics y ETL de lectura.
- `hotel_partner` y `gerente_hotel`: partner, contenido, inventario y reservas manuales.
- `revenue_manager`: revenue operativo y analytics.
- `marketing_hotelero`: contenido partner, promociones y analytics de promociones.
- `cliente`: búsqueda de hoteles, reservas y sesión.

## Protección de rutas

La protección central vive en `src/app/security/middleware.py` y las reglas en `src/app/security/route_permissions.py`.

Las rutas protegidas devuelven:

- `303` a `/auth/login?next=...` si no hay sesión.
- `403` con vista amigable si hay sesión pero el rol no tiene permiso.

## Alcance

No se modificó ETL, Airflow, PocketBase, `fact_hotel_reservations` ni dimensiones.
