# Usuarios demo GA03

Usuarios de demostración preparados para exposición funcional de GA03 sobre el modelo de seguridad en MongoDB.

## Tabla de acceso demo

| Rol | Username | Email | Password demo | Rutas sugeridas para mostrar |
| --- | --- | --- | --- | --- |
| super_admin | `superadmin` | `admin@hoteldata.local` | `Admin12345*` | `/admin/security`, `/etl-status`, `/ta02` |
| operador_datos | `operador` | `operador@hoteldata.local` | `Operador123*` | `/etl-status`, `/analytics/reservations`, `/ta02` |
| auditor_datos | `auditor` | `auditor@hoteldata.local` | `Auditor123*` | `/admin/security`, `/analytics/conversion`, `/audit` |
| hotel_partner | `partner` | `partner@hoteldata.local` | `Partner123*` | `/partner/hotels`, `/partner/hotels/1/content`, `/partner/hotels/1/inventory` |
| gerente_hotel | `gerente` | `gerente@hoteldata.local` | `Gerente123*` | `/partner/hotels/1/performance`, `/analytics/revenue`, `/hotels/search` |
| revenue_manager | `revenue` | `revenue@hoteldata.local` | `Revenue123*` | `/revenue/rate-plans`, `/revenue/promotions`, `/analytics/revenue` |
| marketing_hotelero | `marketing` | `marketing@hoteldata.local` | `Marketing123*` | `/revenue/promotions`, `/analytics/promotions`, `/hotels/compare` |
| cliente | `cliente` | `cliente@hoteldata.local` | `Cliente123*` | `/hotels/search`, `/hotels/compare`, `/reservations/new` |

## Alcance actual

- Los usuarios demo quedan guardados en `users`.
- Cada usuario queda asociado a un único rol principal en `role_ids` y `primary_role`.
- La contraseña queda hasheada con `passlib/bcrypt`.
- El script es idempotente: si el usuario ya existe, se actualiza y no se duplica.
- Cada ejecución registra actividad en `user_activity_logs`.

## Nota funcional

El proyecto ya permite login básico y protección puntual de rutas sensibles como `/auth/me`, `/admin/security` y `/admin/users`.

Todavía no está implementado que:

- la aplicación siempre arranque obligatoriamente en login;
- todo el menú lateral cambie visualmente según rol;
- todas las rutas del sistema estén filtradas por permisos.

Eso significa que estos usuarios demo ya sirven para explicar el modelo de roles y probar login, pero la experiencia completa de menú por rol sigue siendo una fase posterior.
