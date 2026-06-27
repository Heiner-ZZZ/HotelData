# Plan de Implementación: Editar Nombre Comercial

**Branch**: `014-editar-nombre-comercial` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend (Angular)                 Backend (FastAPI)             MongoDB
─────────────────                  ─────────────────             ──────
                                                     ┌──────────────────────┐
  /management/properties/:id/edit ───►               │ properties/service/  │
  (form: nombre_comercial)           PUT              │ profile.py           │──► hotels
                                     /api/partner/   │ (update_profile)     │    (manual_override
                                     properties/     │                      │     + verified_at)
                                     {id}/profile    └──────────────────────┘
                                                        │
                                                     ┌──▼───────────────────┐
                                                     │ hotel_profile_changes│
                                                     │ (audit log)          │
                                                     └──────────────────────┘
```

## Componentes

| Archivo | Propósito |
|---------|-----------|
| `server/src/app/modules/partner/services/profile.py` | `update_hotel_profile()` — valida, actualiza `manual_override`, registra auditoría |
| `server/src/app/modules/partner/routes.py` | Endpoint `PUT /api/partner/properties/{id}/profile` |
| `frontend/src/app/features/partner/pages/property-edit-page/*` | Formulario de edición de nombre comercial |

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/profile | Obtener perfil actual del hotel |
| PUT | /api/partner/properties/{id}/profile | Actualizar nombre comercial y otros campos editables |

## Flujo

1. Partner accede a formulario de edición de propiedad
2. Carga datos actuales desde `GET /api/partner/properties/{id}`
3. Modifica `nombre_comercial` (y otros campos editables)
4. `PUT /api/partner/properties/{id}/profile`:
   - Backend recibe solo campos permitidos (whitelist)
   - Actualiza `manual_override` con `{ field: value, updated_by, updated_at }`
   - Establece `verified_at = now` si cambia nombre
   - Registra cambio en `hotel_profile_changes` con old/new value
5. Respuesta 200 con perfil actualizado

## Colecciones

| Colección | Operación | Detalle |
|-----------|-----------|---------|
| `hotels` | update | `manual_override.nombre_comercial`, `verified_at` |
| `hotel_profile_changes` | insert | `hotel_id`, `field`, `old_value`, `new_value`, `changed_by`, `changed_at` |

## Reglas de negocio

- `prop_id` técnico no se puede modificar (es la clave del sistema)
- `nombre_comercial` se guarda en `manual_override` para no pisar datos del ETL
- Cada cambio se registra en `hotel_profile_changes` (auditoría)
- Solo `hotel_partner`, `gerente_hotel` y `super_admin` pueden editar
- El hotel debe estar asignado al partner (verificación de propiedad)
