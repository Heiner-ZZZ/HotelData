# Casos de uso GA03 - Plataforma HotelData Hub Analytics

GA03 documenta una plataforma web responsiva de reservas hoteleras inspirada en Expedia/Trivago. El avance real de GA03 se concentra en analítica, administración de datos y gobierno ETL. Las funciones de cuenta, pagos, partner central, inventario transaccional y reservas completas quedan planificadas.

## Resumen por estado

- Implementado: CU25, CU29, CU30, CU32.
- Parcial: CU01, CU02, CU03, CU04, CU12, CU24, CU26, CU27, CU28.
- Planificado: CU05, CU06, CU07, CU08, CU09, CU10, CU11, CU13, CU14, CU15, CU16, CU17, CU18, CU19, CU20, CU21, CU22, CU23, CU31.

## Paquete 1: Experiencia del cliente y búsqueda hotelera

### CU01 Buscar hoteles por destino, fecha y ocupación

- ID: CU01
- Paquete: Experiencia del cliente y búsqueda hotelera
- Nombre: Buscar hoteles por destino, fecha y ocupación
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 9
- Tipo: Operativo
- Estado: Parcial
- Propósito: Permitir consultas exploratorias sobre hoteles y reservas con filtros básicos.
- Descripción: En GA03 existe búsqueda analítica sobre registros y dimensiones, pero no un motor transaccional completo de disponibilidad hotelera.
- Historias de usuario:
  - Como usuario operativo, quiero buscar hoteles por destino, para revisar demanda asociada.
  - Como usuario operativo, quiero filtrar por fechas, para analizar periodos específicos.
  - Como usuario operativo, quiero considerar ocupación, para interpretar patrones de viaje.
  - Como usuario operativo, quiero ver resultados ordenados, para comparar opciones rápidamente.
- Imagen del caso de uso implementado: [Pendiente]

### CU02 Filtrar hoteles por precio, estrellas, promoción y servicios

- ID: CU02
- Paquete: Experiencia del cliente y búsqueda hotelera
- Nombre: Filtrar hoteles por precio, estrellas, promoción y servicios
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Parcial
- Propósito: Segmentar hoteles y reservas por atributos comerciales.
- Descripción: GA03 cuenta con dimensiones y métricas de precio, estrellas y promoción; los servicios hoteleros existen como colección documental, pero no hay experiencia final de comprador.
- Historias de usuario:
  - Como usuario operativo, quiero filtrar por precio, para encontrar rangos relevantes.
  - Como usuario operativo, quiero filtrar por estrellas, para comparar categorías hoteleras.
  - Como usuario operativo, quiero filtrar promociones, para revisar impacto comercial.
  - Como usuario operativo, quiero consultar servicios, para contextualizar la oferta.
- Imagen del caso de uso implementado: [Pendiente]

### CU03 Consultar detalle de hotel

- ID: CU03
- Paquete: Experiencia del cliente y búsqueda hotelera
- Nombre: Consultar detalle de hotel
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Parcial
- Propósito: Ver información de una propiedad hotelera.
- Descripción: El sistema expone datos documentales y dimensionales de hoteles, pero no una ficha pública completa de venta.
- Historias de usuario:
  - Como usuario operativo, quiero abrir el detalle de un hotel, para revisar sus atributos.
  - Como usuario operativo, quiero consultar ubicación, para entender su contexto geográfico.
  - Como usuario operativo, quiero revisar calidad del dato, para confiar en el análisis.
  - Como usuario operativo, quiero relacionar hotel con reservas, para evaluar desempeño.
- Imagen del caso de uso implementado: [Pendiente]

### CU04 Comparar hoteles disponibles

- ID: CU04
- Paquete: Experiencia del cliente y búsqueda hotelera
- Nombre: Comparar hoteles disponibles
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 7
- Tipo: Táctico
- Estado: Parcial
- Propósito: Comparar hoteles con base en atributos analíticos.
- Descripción: GA03 permite comparación indirecta mediante filtros, dimensiones y dashboard; la comparación tipo marketplace queda planificada.
- Historias de usuario:
  - Como usuario operativo, quiero comparar hoteles por destino, para detectar mejores opciones.
  - Como usuario operativo, quiero comparar precios, para revisar competitividad.
  - Como usuario operativo, quiero comparar conversión, para evaluar desempeño.
  - Como usuario operativo, quiero comparar promociones, para decidir acciones comerciales.
- Imagen del caso de uso implementado: [Pendiente]

## Paquete 2: Cuenta, sesión y perfil de usuario

### CU05 Registrarse como usuario

- ID: CU05
- Paquete: Cuenta, sesión y perfil de usuario
- Nombre: Registrarse como usuario
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 6
- Tipo: Operativo
- Estado: Planificado
- Propósito: Crear cuentas de usuario para operación personalizada.
- Descripción: GA03 no implementa registro real; se documenta como capacidad futura.
- Historias de usuario:
  - Como usuario operativo, quiero crear una cuenta, para acceder a funciones personalizadas.
  - Como usuario operativo, quiero registrar mis datos básicos, para identificar mi perfil.
  - Como usuario operativo, quiero confirmar mi cuenta, para usar la plataforma con seguridad.
  - Como administrador, quiero revisar usuarios registrados, para gobernar accesos.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU06 Iniciar sesión y validar rol

- ID: CU06
- Paquete: Cuenta, sesión y perfil de usuario
- Nombre: Iniciar sesión y validar rol
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 8
- Tipo: Operativo
- Estado: Planificado
- Propósito: Controlar acceso según rol.
- Descripción: No existe login real ni control de roles implementado; el modelo futuro lo contempla.
- Historias de usuario:
  - Como usuario operativo, quiero iniciar sesión, para entrar de forma segura.
  - Como administrador, quiero validar roles, para limitar acciones sensibles.
  - Como usuario operativo, quiero cerrar sesión, para proteger mi acceso.
  - Como administrador, quiero auditar inicios de sesión, para detectar uso indebido.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU07 Gestionar perfil de viajero

- ID: CU07
- Paquete: Cuenta, sesión y perfil de usuario
- Nombre: Gestionar perfil de viajero
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 5
- Tipo: Operativo
- Estado: Planificado
- Propósito: Mantener preferencias y datos de viajero.
- Descripción: GA03 no implementa perfiles de viajero; queda en modelo futuro.
- Historias de usuario:
  - Como usuario operativo, quiero editar mi perfil, para mantener mis datos actualizados.
  - Como usuario operativo, quiero guardar preferencias, para agilizar búsquedas.
  - Como usuario operativo, quiero administrar hoteles guardados, para comparar opciones.
  - Como usuario operativo, quiero recibir notificaciones, para conocer cambios relevantes.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU08 Consultar historial de actividad

- ID: CU08
- Paquete: Cuenta, sesión y perfil de usuario
- Nombre: Consultar historial de actividad
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 5
- Tipo: Operativo
- Estado: Planificado
- Propósito: Revisar acciones realizadas por usuario.
- Descripción: La auditoría técnica existe para ETL, pero el historial personal de usuario queda planificado.
- Historias de usuario:
  - Como usuario operativo, quiero consultar mi actividad, para recordar búsquedas.
  - Como usuario operativo, quiero ver cambios de perfil, para validar trazabilidad.
  - Como administrador, quiero revisar actividad de usuarios, para auditoría.
  - Como administrador, quiero filtrar acciones por fecha, para investigar eventos.
- Imagen del caso de uso implementado: [No aplica en GA03]

## Paquete 3: Core de reservas hoteleras

### CU09 Crear solicitud de reserva

- ID: CU09
- Paquete: Core de reservas hoteleras
- Nombre: Crear solicitud de reserva
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 10
- Tipo: Operativo
- Estado: Planificado
- Propósito: Iniciar una reserva hotelera.
- Descripción: GA03 analiza eventos de reserva, pero no crea reservas transaccionales reales.
- Historias de usuario:
  - Como usuario operativo, quiero crear una solicitud, para iniciar una reserva.
  - Como usuario operativo, quiero seleccionar fechas, para definir mi estancia.
  - Como usuario operativo, quiero indicar huéspedes, para calcular ocupación.
  - Como usuario operativo, quiero confirmar la solicitud, para continuar el proceso.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU10 Consultar estado de reserva

- ID: CU10
- Paquete: Core de reservas hoteleras
- Nombre: Consultar estado de reserva
- Actor principal: Usuario operativo
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Planificado
- Propósito: Revisar el ciclo de vida de una reserva.
- Descripción: No existe gestión transaccional de estados de reserva; el hecho analítico registra eventos históricos.
- Historias de usuario:
  - Como usuario operativo, quiero ver el estado de mi reserva, para saber si está confirmada.
  - Como usuario operativo, quiero consultar cambios de estado, para entender su evolución.
  - Como usuario operativo, quiero recibir alertas, para reaccionar a cambios.
  - Como administrador, quiero auditar estados, para controlar calidad operativa.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU11 Cancelar reserva según política

- ID: CU11
- Paquete: Core de reservas hoteleras
- Nombre: Cancelar reserva según política
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 7
- Tipo: Operativo
- Estado: Planificado
- Propósito: Cancelar reservas respetando reglas comerciales.
- Descripción: GA03 no implementa cancelaciones ni políticas aplicadas a reservas reales.
- Historias de usuario:
  - Como usuario operativo, quiero cancelar una reserva, para modificar mis planes.
  - Como usuario operativo, quiero ver la política, para conocer cargos.
  - Como administrador, quiero registrar cancelaciones, para auditar operación.
  - Como administrador, quiero analizar cancelaciones, para mejorar políticas.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU12 Registrar reserva manual

- ID: CU12
- Paquete: Core de reservas hoteleras
- Nombre: Registrar reserva manual
- Actor principal: Administrador
- Actores secundarios: Usuario operativo
- Prioridad: 6
- Tipo: Operativo
- Estado: Parcial
- Propósito: Permitir mantenimiento controlado de datos analíticos.
- Descripción: La app ofrece CRUD sobre `fact_hotel_reservations`, pero no una operación transaccional hotelera completa.
- Historias de usuario:
  - Como administrador, quiero crear registros analíticos, para corregir datos puntuales.
  - Como administrador, quiero editar registros, para mantener calidad.
  - Como administrador, quiero eliminar registros erróneos, para depurar información.
  - Como usuario operativo, quiero ver cambios reflejados, para trabajar con datos actualizados.
- Imagen del caso de uso implementado: [Pendiente]

## Paquete 4: Gestión hotelera / Partner Central

### CU13 Administrar perfil del hotel

- ID: CU13
- Paquete: Gestión hotelera / Partner Central
- Nombre: Administrar perfil del hotel
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 7
- Tipo: Operativo
- Estado: Planificado
- Propósito: Gestionar información comercial de una propiedad.
- Descripción: GA03 conserva datos hoteleros, pero no implementa portal partner central.
- Historias de usuario:
  - Como administrador, quiero editar el perfil del hotel, para actualizar información pública.
  - Como administrador, quiero revisar datos de contacto, para mantener comunicación.
  - Como administrador, quiero validar ubicación, para mejorar búsquedas.
  - Como administrador, quiero auditar cambios, para controlar calidad.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU14 Administrar imágenes y contenido del hotel

- ID: CU14
- Paquete: Gestión hotelera / Partner Central
- Nombre: Administrar imágenes y contenido del hotel
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 6
- Tipo: Operativo
- Estado: Planificado
- Propósito: Mantener contenido visual y descriptivo del hotel.
- Descripción: Las colecciones futuras contemplan imágenes, páginas y cambios de contenido.
- Historias de usuario:
  - Como administrador, quiero subir imágenes, para mejorar presentación del hotel.
  - Como administrador, quiero editar descripciones, para mantener contenido vigente.
  - Como administrador, quiero revisar cambios, para aprobar publicaciones.
  - Como usuario operativo, quiero consultar contenido, para evaluar la oferta.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU15 Administrar políticas del hotel

- ID: CU15
- Paquete: Gestión hotelera / Partner Central
- Nombre: Administrar políticas del hotel
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 7
- Tipo: Operativo
- Estado: Planificado
- Propósito: Gestionar reglas de cancelación, estancia y operación.
- Descripción: GA03 no aplica políticas reales; se documentan como modelo futuro.
- Historias de usuario:
  - Como administrador, quiero crear políticas, para regular reservas.
  - Como administrador, quiero actualizar políticas, para responder al negocio.
  - Como usuario operativo, quiero consultar políticas, para tomar decisiones.
  - Como administrador, quiero auditar políticas, para cumplir control interno.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU16 Consultar rendimiento de propiedades

- ID: CU16
- Paquete: Gestión hotelera / Partner Central
- Nombre: Consultar rendimiento de propiedades
- Actor principal: Administrador
- Actores secundarios: Usuario operativo
- Prioridad: 8
- Tipo: Táctico
- Estado: Planificado
- Propósito: Evaluar resultados comerciales por propiedad desde una vista partner.
- Descripción: La analítica por hotel existe parcialmente en dashboard, pero la vista partner queda fuera de GA03.
- Historias de usuario:
  - Como administrador, quiero ver rendimiento por hotel, para priorizar acciones.
  - Como administrador, quiero revisar reservas por propiedad, para medir demanda.
  - Como usuario operativo, quiero consultar métricas, para apoyar decisiones.
  - Como administrador, quiero comparar objetivos, para evaluar cumplimiento.
- Imagen del caso de uso implementado: [No aplica en GA03]

## Paquete 5: Habitaciones, inventario y disponibilidad

### CU17 Administrar tipos de habitación

- ID: CU17
- Paquete: Habitaciones, inventario y disponibilidad
- Nombre: Administrar tipos de habitación
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Planificado
- Propósito: Definir habitaciones comercializables.
- Descripción: GA03 no maneja inventario de habitaciones real.
- Historias de usuario:
  - Como administrador, quiero crear tipos de habitación, para organizar inventario.
  - Como administrador, quiero asociar amenidades, para describir cada tipo.
  - Como administrador, quiero editar capacidades, para ajustar ocupación.
  - Como usuario operativo, quiero consultar tipos, para entender disponibilidad.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU18 Administrar inventario por calendario

- ID: CU18
- Paquete: Habitaciones, inventario y disponibilidad
- Nombre: Administrar inventario por calendario
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 9
- Tipo: Operativo
- Estado: Planificado
- Propósito: Controlar disponibilidad por fecha.
- Descripción: El modelo futuro incluye calendario de inventario, sin implementación en GA03.
- Historias de usuario:
  - Como administrador, quiero cargar inventario por fecha, para controlar disponibilidad.
  - Como administrador, quiero ver ocupación por calendario, para planificar ventas.
  - Como administrador, quiero ajustar cupos, para responder a demanda.
  - Como usuario operativo, quiero consultar disponibilidad, para evitar sobreventa.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU19 Bloquear fechas no disponibles

- ID: CU19
- Paquete: Habitaciones, inventario y disponibilidad
- Nombre: Bloquear fechas no disponibles
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 7
- Tipo: Operativo
- Estado: Planificado
- Propósito: Evitar venta en fechas restringidas.
- Descripción: GA03 no gestiona bloqueos de disponibilidad.
- Historias de usuario:
  - Como administrador, quiero bloquear fechas, para evitar reservas no válidas.
  - Como administrador, quiero indicar motivo, para dejar trazabilidad.
  - Como administrador, quiero levantar bloqueos, para reactivar inventario.
  - Como usuario operativo, quiero ver bloqueos, para explicar indisponibilidad.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU20 Sincronizar disponibilidad con PMS / Channel Manager

- ID: CU20
- Paquete: Habitaciones, inventario y disponibilidad
- Nombre: Sincronizar disponibilidad con PMS / Channel Manager
- Actor principal: Administrador
- Actores secundarios: Sistemas técnicos externos
- Prioridad: 8
- Tipo: Estratégico
- Estado: Planificado
- Propósito: Integrar disponibilidad con sistemas hoteleros externos.
- Descripción: Se documenta como integración futura; no se conecta al ETL GA03 actual.
- Historias de usuario:
  - Como administrador, quiero conectar un PMS, para sincronizar disponibilidad.
  - Como administrador, quiero revisar logs de sincronización, para detectar fallos.
  - Como administrador, quiero mapear canales, para mantener consistencia.
  - Como usuario operativo, quiero consultar disponibilidad actualizada, para operar con confianza.
- Imagen del caso de uso implementado: [No aplica en GA03]

## Paquete 6: Tarifas, promociones y revenue

### CU21 Administrar planes tarifarios

- ID: CU21
- Paquete: Tarifas, promociones y revenue
- Nombre: Administrar planes tarifarios
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Planificado
- Propósito: Definir estructuras tarifarias por hotel.
- Descripción: GA03 analiza precios históricos, pero no administra planes tarifarios.
- Historias de usuario:
  - Como administrador, quiero crear planes tarifarios, para comercializar habitaciones.
  - Como administrador, quiero editar reglas de tarifa, para adaptar precios.
  - Como usuario operativo, quiero consultar planes, para entender oferta.
  - Como administrador, quiero auditar cambios, para mantener control.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU22 Configurar tarifas por fecha

- ID: CU22
- Paquete: Tarifas, promociones y revenue
- Nombre: Configurar tarifas por fecha
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 8
- Tipo: Operativo
- Estado: Planificado
- Propósito: Mantener calendario de precios.
- Descripción: El modelo futuro incluye `hotel_rate_calendar`; no está implementado en GA03.
- Historias de usuario:
  - Como administrador, quiero fijar tarifas por fecha, para responder a temporada.
  - Como administrador, quiero aplicar reglas, para automatizar precios.
  - Como usuario operativo, quiero consultar tarifas, para revisar coherencia.
  - Como administrador, quiero detectar anomalías, para evitar errores comerciales.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU23 Crear campañas promocionales

- ID: CU23
- Paquete: Tarifas, promociones y revenue
- Nombre: Crear campañas promocionales
- Actor principal: Administrador
- Actores secundarios: Usuario operativo
- Prioridad: 7
- Tipo: Táctico
- Estado: Planificado
- Propósito: Configurar promociones comerciales.
- Descripción: GA03 registra `promotion_flag` en datos analíticos, pero no crea campañas reales.
- Historias de usuario:
  - Como administrador, quiero crear campañas, para impulsar demanda.
  - Como administrador, quiero asociar cupones, para medir conversión.
  - Como usuario operativo, quiero consultar campañas, para analizar resultados.
  - Como administrador, quiero pausar campañas, para controlar presupuesto.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU24 Evaluar impacto de promociones

- ID: CU24
- Paquete: Tarifas, promociones y revenue
- Nombre: Evaluar impacto de promociones
- Actor principal: Administrador
- Actores secundarios: Usuario operativo
- Prioridad: 8
- Tipo: Táctico
- Estado: Parcial
- Propósito: Analizar relación entre promoción, clic y reserva.
- Descripción: El modelo dimensional incluye promoción y reservas; las visualizaciones avanzadas quedan en evolución.
- Historias de usuario:
  - Como administrador, quiero medir reservas con promoción, para evaluar efectividad.
  - Como usuario operativo, quiero comparar eventos promovidos, para detectar patrones.
  - Como administrador, quiero revisar ingresos, para justificar campañas.
  - Como usuario operativo, quiero filtrar por destino, para ver diferencias regionales.
- Imagen del caso de uso implementado: [Pendiente]

## Paquete 7: Analytics, BI y toma de decisiones

### CU25 Consultar dashboard de reservas

- ID: CU25
- Paquete: Analytics, BI y toma de decisiones
- Nombre: Consultar dashboard de reservas
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 9
- Tipo: Estratégico
- Estado: Implementado
- Propósito: Presentar métricas de reservas y operación analítica.
- Descripción: La app expone dashboard y vistas de consulta sobre MongoDB con datos cargados por ETL.
- Historias de usuario:
  - Como usuario operativo, quiero ver métricas principales, para entender el estado del negocio.
  - Como administrador, quiero revisar conteos, para validar disponibilidad de datos.
  - Como usuario operativo, quiero navegar a reservas, para explorar detalles.
  - Como administrador, quiero ver calidad, para detectar riesgos de datos.
- Imagen del caso de uso implementado: [Pendiente]

### CU26 Analizar conversión búsqueda-click-reserva

- ID: CU26
- Paquete: Analytics, BI y toma de decisiones
- Nombre: Analizar conversión búsqueda-click-reserva
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 9
- Tipo: Estratégico
- Estado: Parcial
- Propósito: Medir embudo desde búsqueda hasta reserva.
- Descripción: Existen campos `click_bool` y `reserva_bool`; la analítica visual avanzada es parcial.
- Historias de usuario:
  - Como usuario operativo, quiero medir clics, para evaluar interés.
  - Como usuario operativo, quiero medir reservas, para conocer conversión.
  - Como administrador, quiero cruzar conversión por destino, para priorizar mercados.
  - Como administrador, quiero comparar canales, para optimizar inversión.
- Imagen del caso de uso implementado: [Pendiente]

### CU27 Analizar ingresos brutos por hotel y destino

- ID: CU27
- Paquete: Analytics, BI y toma de decisiones
- Nombre: Analizar ingresos brutos por hotel y destino
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 8
- Tipo: Estratégico
- Estado: Parcial
- Propósito: Evaluar ingresos calculados por reservas.
- Descripción: `fact_hotel_reservations` incluye `reservas_brutas_usd`; los tableros avanzados quedan parciales.
- Historias de usuario:
  - Como usuario operativo, quiero sumar ingresos por hotel, para identificar propiedades clave.
  - Como usuario operativo, quiero sumar ingresos por destino, para analizar mercado.
  - Como administrador, quiero revisar precios, para validar coherencia.
  - Como administrador, quiero exportar evidencia, para presentaciones.
- Imagen del caso de uso implementado: [Pendiente]

### CU28 Analizar comportamiento por país visitante y canal

- ID: CU28
- Paquete: Analytics, BI y toma de decisiones
- Nombre: Analizar comportamiento por país visitante y canal
- Actor principal: Usuario operativo
- Actores secundarios: Administrador
- Prioridad: 8
- Tipo: Estratégico
- Estado: Parcial
- Propósito: Segmentar demanda por origen y canal.
- Descripción: Las dimensiones `dim_visitor_countries` y `dim_sites` existen; el análisis visual dedicado es parcial.
- Historias de usuario:
  - Como usuario operativo, quiero analizar país visitante, para entender origen de demanda.
  - Como usuario operativo, quiero analizar sitio/canal, para evaluar desempeño.
  - Como administrador, quiero cruzar país con reservas, para detectar mercados fuertes.
  - Como administrador, quiero cruzar canal con promoción, para mejorar estrategia.
- Imagen del caso de uso implementado: [Pendiente]

## Paquete 8: Administración, datos, ETL y gobierno

### CU29 Ejecutar pipeline ETL de reservas

- ID: CU29
- Paquete: Administración, datos, ETL y gobierno
- Nombre: Ejecutar pipeline ETL de reservas
- Actor principal: Administrador
- Actores secundarios: PocketBase, MongoDB
- Prioridad: 10
- Tipo: Operativo
- Estado: Implementado
- Propósito: Cargar datos analíticos desde fuente operacional hacia MongoDB.
- Descripción: GA03 conserva el flujo CSV -> PocketBase como preparación administrativa y PocketBase -> JSONL -> Parquet -> MongoDB como ETL principal.
- Historias de usuario:
  - Como administrador, quiero ejecutar el pipeline, para cargar reservas en MongoDB.
  - Como administrador, quiero ver progreso del ETL, para monitorear la ejecución.
  - Como administrador, quiero evitar duplicados, para mantener consistencia.
  - Como administrador, quiero conservar reportes, para demostrar trazabilidad.
- Imagen del caso de uso implementado: [Pendiente]

### CU30 Validar Parquet, calidad y registros rechazados

- ID: CU30
- Paquete: Administración, datos, ETL y gobierno
- Nombre: Validar Parquet, calidad y registros rechazados
- Actor principal: Administrador
- Actores secundarios: MongoDB
- Prioridad: 10
- Tipo: Operativo
- Estado: Implementado
- Propósito: Verificar que los artefactos y reportes de calidad sean correctos.
- Descripción: La sección `/etl-status` muestra validación, Parquet, reportes y registros rechazados cuando existen.
- Historias de usuario:
  - Como administrador, quiero validar el dataset, para confirmar que cumple TARGET_RECORDS.
  - Como administrador, quiero confirmar Parquet, para asegurar el formato analítico.
  - Como administrador, quiero revisar rechazados, para detectar errores de calidad.
  - Como administrador, quiero consultar reportes, para soportar la evidencia del proyecto.
- Imagen del caso de uso implementado: [Pendiente]

### CU31 Administrar usuarios, roles y permisos

- ID: CU31
- Paquete: Administración, datos, ETL y gobierno
- Nombre: Administrar usuarios, roles y permisos
- Actor principal: Administrador
- Actores secundarios: Ninguno
- Prioridad: 9
- Tipo: Operativo
- Estado: Planificado
- Propósito: Gobernar acceso a la plataforma.
- Descripción: No hay login ni roles reales en GA03; las colecciones futuras documentan esta capacidad.
- Historias de usuario:
  - Como administrador, quiero crear usuarios, para habilitar acceso controlado.
  - Como administrador, quiero asignar roles, para limitar permisos.
  - Como administrador, quiero revocar accesos, para proteger información.
  - Como administrador, quiero auditar cambios, para cumplir gobierno.
- Imagen del caso de uso implementado: [No aplica en GA03]

### CU32 Consultar auditoría y trazabilidad de ejecuciones

- ID: CU32
- Paquete: Administración, datos, ETL y gobierno
- Nombre: Consultar auditoría y trazabilidad de ejecuciones
- Actor principal: Administrador
- Actores secundarios: MongoDB
- Prioridad: 9
- Tipo: Táctico
- Estado: Implementado
- Propósito: Revisar evidencias técnicas y funcionales de ejecución.
- Descripción: Existen reportes, auditoría y trazabilidad de ETL desde las vistas y reportes actuales. La auditoría de usuarios queda futura.
- Historias de usuario:
  - Como administrador, quiero consultar ejecuciones, para demostrar proceso.
  - Como administrador, quiero revisar calidad, para validar resultados.
  - Como administrador, quiero ver errores controlados, para diagnosticar problemas.
  - Como administrador, quiero conservar evidencia histórica, para sustentar entregas.
- Imagen del caso de uso implementado: [Pendiente]
