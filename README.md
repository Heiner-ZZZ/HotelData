# HotelData

<p align="center">
  <img src="frontend/src/assets/logo-hoteldata.png" alt="HotelData Logo" width="200">
</p>

<p align="center">
  <strong>Plataforma de gestión hotelera todo-en-uno</strong><br>
  Angular 22 · FastAPI · MongoDB
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Angular-22-DD0031?logo=angular" alt="Angular 22">
  <img src="https://img.shields.io/badge/FastAPI-1.0.0-009688?logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/MongoDB-8.0-47A248?logo=mongodb" alt="MongoDB">
  <img src="https://img.shields.io/badge/Python-3.13-3776AB?logo=python" alt="Python 3.13">
  <img src="https://img.shields.io/badge/TypeScript-6.x-3178C6?logo=typescript" alt="TypeScript 6">
</p>

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| **Frontend** | Angular 22 · TypeScript 6.x · Signals · SCSS · OnPush |
| **Backend** | FastAPI · Python 3.13 · Pydantic v2 · Async |
| **Base de datos** | MongoDB 8.0 (motor transaccional + réplica set) |
| **Infraestructura** | Docker Compose · Nginx · Node 24 Alpine |
| **ETL / Data** | Airflow · PocketBase |

## Módulos del sistema

### Frontend (34 módulos)

| Módulo | Descripción |
|--------|------------|
| `account` | Perfil y preferencias de usuario |
| `admin` | Administración global del sistema |
| `amenities` | Catálogo y gestión de amenities |
| `availability` | Calendario de disponibilidad y tarifas |
| `billing` | Facturación, folios y cargos |
| `check-ins` | Proceso de check-in |
| `check-outs` | Proceso de check-out con liquidación |
| `expenses` | Gestión de gastos y ledger contable |
| `guests` | Módulo de huéspedes |
| `hotel-compare` | Comparador de hoteles |
| `hotel-detail` | Detalle y galería de hoteles |
| `hotel-search` | Búsqueda con filtros y mapa |
| `housekeeping` | Limpieza, mantenimiento y estado de habitaciones |
| `hr` | RRHH: empleados, asistencia, turnos, onboarding |
| `in-stay` | Portal de huésped y bandeja del staff |
| `lost-and-found` | Objetos perdidos |
| `management` | Reportes, auditoría, configuración |
| `map` | Editor de destinos y mapa |
| `notifications` | Campaña de notificaciones |
| `policies` | Políticas de propiedad |
| `properties` | Gestión de propiedades |
| `rates` | Tarifas, planes y calendario de precios |
| `reservations` | Reservas, planner y calendario de recepción |
| `reviews` | Reseñas y reputación |
| `rooms` | Tipos de habitación y rooms grid |
| `shifts` | Control de turnos y caja |
| `system-admin` | Usuarios del sistema y auditoría |
| `onboarding` / `ownership` / `reception` / `welcome` | Módulos complementarios |

### Backend (27 módulos)

| Módulo | Descripción |
|--------|------------|
| `account` | Cuenta de usuario y perfil |
| `admin` | Rutas de administración |
| `amenities` | CRUD de amenities |
| `audit` | Registro de auditoría |
| `auth` | Autenticación y registro |
| `billing` | Facturación, folios, pagos |
| `expenses` | Gastos y ledger |
| `geo_catalog` | Catálogo geográfico |
| `global_settings` | Configuración global |
| `hotels` | Detalle, búsqueda y availability |
| `housekeeping` | Limpieza, mantenimiento, dashboard |
| `hr` | RRHH: empleados, turnos |
| `instay` | Estancia activa y portal huésped |
| `kpi` | Balanced Scorecard y KPIs |
| `lost_and_found` | Objetos perdidos |
| `map` | Destinos y mapas |
| `notifications` | Notificaciones push |
| `partner` | Partner: content, rates, rooms, dashboard |
| `payments` | Procesador de pagos |
| `reception` | Calendario de recepción y turnos |
| `reports` | Exportación PDF/Excel |
| `reservations` | Ciclo de vida completo de reservas |
| `revenue` | Promociones y revenue management |
| `reviews` | Reseñas y reports |
| `settings` | Preferencias del sistema |
| `tracking` | Tracking de eventos |
| `users` | Usuarios y roles |

## Fast facts

- ~**866+ commits** en `ta06-integrations`
- **379** archivos Python
- **426** componentes TypeScript
- **373** partials SCSS
- **140** templates HTML
- **58** colecciones en MongoDB modeladas

## Cómo ejecutar

### Desarrollo (Docker)

```bash
docker compose -f infra/docker-compose.yml up -d
```

### Frontend standalone

```bash
cd frontend
npm install
npm run dev
```

### Backend standalone

```bash
cd server
pip install -r requirements.txt
uvicorn src.app.main:app --reload
```
