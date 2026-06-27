# Plan: Gestionar Geolocalización

**Branch**: `feature/052-gestionar-geolocalizacion`

## Componentes
- `server/src/app/modules/geo/` - Rutas y servicios geoespaciales
- `frontend/src/app/features/geo/` - DestinationMapComponent, DestinationEditor

## Endpoints
| GET | /geo/destinations | Gestor geoespacial HTML |
| PUT | /api/geo/destinations/{id} | Actualizar metadata |
| GET | /api/geo/destinations/{id}/map | Datos para mapa |