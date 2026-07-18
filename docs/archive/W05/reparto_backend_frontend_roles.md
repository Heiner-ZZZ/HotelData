# Reparto de Backend, Frontend y Funcionalidades por Rol

## 1. Vision general del proyecto

HotelData esta dividido en dos grandes capas funcionales:

- `backend`: FastAPI en `src/app` para autenticacion, autorizacion, APIs, logica de negocio y acceso a datos.
- `frontend`: Angular en `frontend/src/app` para login, navegacion, vistas, formularios y experiencia por rol.

Adicionalmente, el proyecto tiene una tercera capa de soporte:

- `etl / datos`: procesos Python y Airflow en `src/etl` y `dags` para extraccion, transformacion, calidad, auditoria y carga de datos.

## 2. Que hace el backend

El backend centraliza la logica del sistema y expone rutas para que el frontend consuma informacion o ejecute acciones.

### Responsabilidades principales del backend

- autenticar usuarios y crear sesiones;
- identificar el `primary_role` del usuario;
- proteger rutas con reglas de acceso por rol y permiso;
- exponer APIs para hoteles, reservas, partner, revenue, auditoria, administracion y configuracion;
- consultar y actualizar MongoDB;
- inicializar colecciones e indices base al arrancar la aplicacion;
- servir como puente entre la interfaz y los datos reales.

### Archivos backend clave

- `src/app/main.py`: arranque de FastAPI e integracion de routers.
- `src/app/security/route_permissions.py`: reglas de acceso por rol y permiso.
- `src/app/security/middleware.py`: aplica la proteccion de rutas.
- `src/app/modules/auth/*`: login, sesion y usuario autenticado.
- `src/app/modules/admin/*`: usuarios, permisos y funciones de sistema.
- `src/app/modules/partner/*`: gestion hotelera operativa.
- `src/app/modules/revenue/*`: tarifas, mercados, promociones y revenue.
- `src/app/modules/reservations/*`: reservas y flujo operativo.
- `src/app/modules/account/*`: datos de cuenta y perfil.
- `src/database/*`: conexion, repositorios e indices.

## 3. Que hace el frontend

El frontend muestra la experiencia visual y decide que pantallas, menus y acciones ve cada usuario segun su rol.

### Responsabilidades principales del frontend

- mostrar login y redireccionar al inicio correcto segun rol;
- cargar la sesion actual;
- ocultar o mostrar menus segun `allowedRoles`;
- proteger rutas con guards;
- consumir APIs del backend;
- renderizar modulos de gestion, sistema, cuenta y experiencia publica;
- separar experiencias de `management`, `system`, `account` y `public`.

### Archivos frontend clave

- `frontend/src/app/app.routes.ts`: rutas principales y shells.
- `frontend/src/app/core/auth/auth.guard.ts`: proteccion de rutas.
- `frontend/src/app/core/auth/auth.service.ts`: estado de sesion.
- `frontend/src/app/shared/ui/access-nav/access-nav.ts`: navegacion filtrada por rol.
- `frontend/src/app/shared/ui/sidebar-nav/sidebar-nav.ts`: sidebar por rol.
- `frontend/src/app/features/system-admin/*`: vistas del area de sistema.
- `frontend/src/app/features/management/*`: vistas de gestion hotelera.
- `frontend/src/app/features/account/*`: perfil y cuenta del cliente.
- `frontend/src/app/features/hotel-search/*`: experiencia publica de busqueda.

## 4. Como se reparte la responsabilidad entre backend y frontend

### Backend

- decide si un usuario puede o no puede acceder;
- valida permisos reales;
- ejecuta la logica de negocio;
- entrega o persiste datos.

### Frontend

- organiza la navegacion;
- presenta formularios, tablas y dashboards;
- muestra solo lo que corresponde a cada rol;
- llama a las APIs correctas del backend.

### Regla importante

Aunque el frontend oculte una opcion, la autorizacion real debe seguir existiendo en backend. En este proyecto eso se controla sobre todo desde `src/app/security/route_permissions.py`.

## 5. Roles existentes

Los roles que hoy aparecen implementados en la navegacion, documentacion y control de acceso son:

- `super_admin`
- `admin_sistema`
- `hotel_partner`
- `gerente_hotel`
- `revenue_manager`
- `marketing_hotelero`
- `operador_datos`
- `auditor_datos`
- `cliente`

## 6. Reparto de funcionalidades por rol

### 6.1 `super_admin`

Es el rol con mayor alcance funcional.

#### Backend

- puede consumir rutas administrativas de usuarios y permisos;
- puede acceder a auditoria, monitoreo y modulos de gestion;
- puede operar reservas, disponibilidad, propiedades, habitaciones, tarifas, politicas, amenities y reportes;
- puede usar capacidades protegidas por permisos altos como `users.manage`.

#### Frontend

- ve navegacion de `Gestion` y `Sistema`;
- accede a `/management/*` y `/system/*`;
- tiene acceso visible a usuarios, permisos, auditoria y monitoreo.

### 6.2 `admin_sistema`

Administra la plataforma casi al mismo nivel que `super_admin`, con foco en operacion del sistema.

#### Backend

- puede gestionar usuarios y permisos;
- puede acceder a dashboard, auditoria, monitoreo y configuracion;
- puede entrar a modulos de gestion y sistema.

#### Frontend

- ve menu completo de `Gestion` y `Sistema`;
- entra a `/system/users`, `/system/permissions`, `/system/audit` y `/system/monitoring`;
- tambien puede navegar los modulos hoteleros operativos.

### 6.3 `hotel_partner`

Representa al socio hotelero con capacidad operativa sobre su propiedad.

#### Backend

- puede usar rutas de gestion hotelera;
- puede trabajar con reservas, disponibilidad, propiedades, habitaciones, tarifas, politicas, amenities, reportes y configuracion;
- no administra usuarios globales ni permisos del sistema.

#### Frontend

- ve shell de `management`;
- accede al panel hotelero y a la mayoria de modulos operativos;
- no ve el menu `Sistema`.

### 6.4 `gerente_hotel`

Rol enfocado en operacion diaria del hotel.

#### Backend

- puede operar reservas, disponibilidad, check-ins y check-outs;
- puede trabajar con habitaciones, politicas y reportes;
- tiene acceso mas limitado sobre propiedades y configuracion;
- no administra usuarios globales.

#### Frontend

- ve `management`;
- tiene acceso a check-ins y check-outs;
- no muestra `Propiedades` en el sidebar principal como modulo destacado;
- no ve el menu `Sistema`.

### 6.5 `revenue_manager`

Rol especializado en precios, inventario comercial y analitica de ingresos.

#### Backend

- puede leer y gestionar funciones de revenue;
- puede trabajar con disponibilidad, tarifas, propiedades y reportes;
- no tiene funciones operativas de check-in/check-out ni administracion global de usuarios.

#### Frontend

- entra a `management`;
- ve rutas como tarifas, disponibilidad, propiedades y reportes;
- no ve opciones de sistema ni operacion hotelera presencial.

### 6.6 `marketing_hotelero`

Rol orientado a contenido comercial, presentacion y apoyo promocional.

#### Backend

- puede acceder a contenido partner, propiedades, politicas, amenities y reportes;
- su alcance de escritura operativa es menor que el de `hotel_partner` o `revenue_manager`;
- no administra usuarios ni permisos globales.

#### Frontend

- ve `management`;
- puede entrar a propiedades, politicas, amenities y reportes;
- no ve check-ins, check-outs ni tarifas como rol principal;
- no ve `Sistema`.

### 6.7 `operador_datos`

Rol tecnico orientado a seguimiento operativo del dato y del sistema.

#### Backend

- puede acceder a auditoria y monitoreo;
- puede usar reportes y algunos flujos asociados a ETL segun permisos;
- no administra usuarios ni permisos globales salvo que el backend le otorgue permisos explicitos adicionales.

#### Frontend

- ve `management` con foco en reportes;
- ve `system` con acceso a auditoria y monitoreo;
- no ve `Usuarios` ni `Permisos`.

### 6.8 `auditor_datos`

Rol de lectura y control sobre trazabilidad, calidad y evidencia.

#### Backend

- puede acceder a auditoria y monitoreo en modo controlado;
- normalmente trabaja con permisos de lectura;
- no debe ejecutar acciones administrativas globales ni cambios operativos mayores.

#### Frontend

- ve `management` para reportes;
- ve `system` para auditoria y monitoreo;
- no ve `Usuarios` ni `Permisos`;
- su experiencia esta orientada mas a revisar que a modificar.

### 6.9 `cliente`

Es el usuario final tipo viajero.

#### Backend

- puede autenticarse;
- puede consultar su cuenta y sus reservas;
- puede acceder a experiencia publica de hoteles;
- no entra al area de gestion ni al sistema interno.

#### Frontend

- usa shells `public` y `account`;
- accede a `/search`, `/hotels/:id`, `/account/bookings` y `/account/profile`;
- no ve menus internos de gestion ni sistema.

## 7. Resumen rapido por zonas funcionales

### Zona publica

- principal rol: `cliente`
- frontend: busqueda, detalle de hotel, perfil, reservas del viajero
- backend: hoteles publicos, cuenta y reservas del cliente

### Zona de gestion hotelera

- roles principales: `super_admin`, `admin_sistema`, `hotel_partner`, `gerente_hotel`, `revenue_manager`, `marketing_hotelero`
- frontend: dashboard, reservas, disponibilidad, propiedades, habitaciones, tarifas, politicas, amenities, reportes, configuracion
- backend: APIs de partner, revenue, reservations, settings y dashboards

### Zona de sistema

- roles principales: `super_admin`, `admin_sistema`, `operador_datos`, `auditor_datos`
- frontend: usuarios, permisos, auditoria y monitoreo
- backend: control de acceso, auditoria, administracion de usuarios, permisos y monitoreo

## 8. Relacion con ETL y datos

Los roles web no cambian el ETL principal, pero algunos si pueden ver o monitorear resultados.

- `super_admin` y `admin_sistema`: mayor control de sistema;
- `operador_datos`: seguimiento operativo;
- `auditor_datos`: revision y evidencia;
- roles hoteleros: consumen resultados ya procesados en dashboards, reportes y vistas de gestion.

La ejecucion de ETL, calidad y carga de datos vive en:

- `src/etl/*`
- `dags/*`

Eso significa que la capa de datos esta separada de la capa visual y de la capa de negocio web.

## 9. Conclusion

La arquitectura actual reparte responsabilidades de forma clara:

- el `backend` controla seguridad, negocio, APIs y datos;
- el `frontend` controla experiencia, navegacion y visibilidad por rol;
- el `etl` procesa y prepara la informacion analitica.

Los roles no estan pensados para que todos vean lo mismo. Cada uno entra a una combinacion distinta de modulos segun su funcion:

- administradores globales: sistema + gestion;
- roles hoteleros: gestion;
- roles de datos: reportes + auditoria/monitoreo;
- cliente: experiencia publica + cuenta personal.
