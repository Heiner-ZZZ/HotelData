# Brief para Google Stitch - HotelData Analytics

## Objetivo de este documento

Este documento sirve como prompt base para pedirle a Google Stitch que genere alrededor de 15 plantillas de interfaz para el proyecto **HotelData Analytics**, manteniendo una linea visual cercana a Expedia/Hotels/Trivago, pero adaptada a un producto de analitica, operacion hotelera y gobierno de datos.

Tambien resume el estado real del proyecto para que Stitch no diseñe una app imaginaria desconectada de lo que ya existe.

## Contexto del proyecto

HotelData Analytics es una plataforma orientada al sector hotelero que combina:

- exploracion de hoteles y reservas con una experiencia visual inspirada en Expedia;
- analitica comercial y operativa;
- gobierno de datos;
- monitoreo de ETL;
- administracion por roles;
- soporte para usuarios tipo cliente, partner hotelero, revenue manager, operador de datos y administrador.

La plataforma **no es solo un buscador de hoteles** y **no es solo un dashboard ETL**. Es un sistema hibrido que une experiencia estilo OTA con capa administrativa y analitica.

## Mision

Proveer informacion hotelera y de reservas confiable, normalizada, trazable y consultable para apoyar decisiones operativas, comerciales y de gobierno de datos en el ecosistema turistico.

## Vision

Convertirse en una plataforma de referencia para gestion, analitica y gobierno de datos hoteleros, con una experiencia moderna que permita a distintos tipos de usuario ver exactamente la informacion que necesitan.

## Objetivos del producto

### Objetivos estrategicos

- Centralizar un dataset hotelero y de reservas de alto volumen.
- Transformar datos operacionales en informacion util para negocio.
- Unificar experiencia de consulta, operacion, revenue y auditoria en una sola plataforma.
- Mantener una interfaz que se sienta cercana a Expedia, pero con capacidades administrativas y analiticas reales.

### Objetivos tacticos

- Implementar un flujo ETL verificable y trazable.
- Convertir datos fuente en hechos y dimensiones analiticas.
- Exponer paneles, busquedas, CRUD y vistas operativas segun rol.
- Permitir que la IA y la interfaz presenten informacion coherente a cada perfil de usuario.

### Objetivos operacionales

- Extraer eventos y reservas desde una fuente tipo Expedia/PocketBase.
- Procesar el flujo `PocketBase -> JSONL -> Parquet -> MongoDB`.
- Registrar calidad, rechazos, auditoria y estado de ejecucion.
- Mostrar busqueda hotelera, detalle, comparacion, reservas, partner, revenue, seguridad y monitoreo ETL.

## Dataset y base de datos

El proyecto trabaja con un dataset hotelero/reservas inspirado en **Expedia** y aterrizado en una coleccion operativa llamada:

- `hotel_reservation_events_03`

Configuracion relevante ya vista en el proyecto:

- `TASK_NUMBER=03`
- `TARGET_RECORDS=300000`
- ETL principal: `PocketBase -> JSONL -> Parquet -> MongoDB`
- Hecho principal: `fact_hotel_reservations`
- Dimensiones activas: 12

La experiencia visual debe sentirse como una evolucion de un portal estilo Expedia, pero conectada a una base analitica real.

## Stack y arquitectura que Stitch debe respetar conceptualmente

El sistema ya contempla y/o usa estos componentes:

- `ETL` en Python
- `Airflow` como orquestador
- `MongoDB` como base principal de consulta
- `Redis` como cache opcional y progresivo
- `Docker` / `docker-compose` para entorno local
- `PocketBase` como fuente operacional y apoyo de integracion
- `FastAPI` como backend actual
- `Angular` como frontend en migracion progresiva

Stitch no debe proponer una interfaz que ignore este stack. El diseño debe comunicar que existe:

- capa publica para busqueda;
- capa autenticada por rol;
- capa operativa/administrativa;
- capa analitica;
- capa de monitoreo de datos.

## Alcance actual del proyecto

### Lo mas avanzado

- Busqueda de hoteles con filtros.
- Detalle de hotel.
- Comparacion de hoteles.
- Solicitud de reserva basica.
- Vistas de partner hotelero.
- Vistas de revenue y promociones.
- Dashboard y analytics.
- Estado ETL, calidad, rechazados y trazabilidad.
- Modelo de seguridad con usuarios, roles y permisos.
- Infraestructura con MongoDB, Redis, PocketBase y Docker Compose.

### Lo que esta parcial

- Experiencia completa de login y navegacion 100% filtrada por rol.
- Reservas transaccionales reales con disponibilidad y pagos.
- PMS / channel manager / inventario totalmente operativo.
- CMS hotelero enriquecido.
- Consolidacion completa de toda la UI en Angular.

### Evaluacion honesta del avance

Veo el proyecto como:

- **70% avanzado** en arquitectura, ETL, modelo de datos, seguridad base y experiencia analitica.
- **55% avanzado** en experiencia funcional multirol.
- **40% avanzado** en experiencia tipo OTA completa para cliente final.

En otras palabras: la base tecnica ya es seria y defendible; la parte que mas necesita diseño consistente es la experiencia de producto por rol.

## Usuarios y que espera ver cada uno

La IA debe mostrar cosas distintas segun el tipo de usuario. No todos deben ver el mismo dashboard ni el mismo menu.

### 1. Cliente / viajero

Espera ver:

- buscador de hoteles tipo Expedia;
- filtros por destino, fechas, ocupacion, estrellas, precio y promociones;
- cards visuales de hoteles;
- detalle de hotel;
- comparador;
- flujo simple para iniciar una reserva;
- historial o seguimiento de su solicitud.

No espera ver:

- ETL, logs tecnicos, MongoDB, trazabilidad interna, seguridad o CRUD tecnico.

### 2. Hotel partner

Espera ver:

- listado de sus propiedades;
- perfil de hotel;
- contenido del hotel;
- imagenes;
- politicas;
- habitaciones;
- inventario basico;
- rendimiento de su propiedad.

No espera ver:

- panel tecnico de ETL completo ni seguridad global del sistema.

### 3. Gerente de hotel

Espera ver:

- KPIs de rendimiento por propiedad;
- reservas, ingresos, conversion y demanda;
- disponibilidad resumida;
- contenido y operacion basica del hotel;
- alertas o desviaciones comerciales.

### 4. Revenue manager

Espera ver:

- revenue por hotel y destino;
- promociones;
- planes tarifarios;
- calendario de tarifas;
- comparativos de conversion;
- elasticidad comercial y resultados de campañas.

### 5. Marketing hotelero

Espera ver:

- campañas promocionales;
- comparacion entre hoteles o segmentos;
- conversion por canal;
- comportamiento de usuario;
- contenidos comerciales y ofertas visibles.

### 6. Operador de datos

Espera ver:

- estado ETL;
- progreso de cargas;
- validaciones;
- calidad de datos;
- rechazados;
- ejecuciones;
- trazabilidad;
- datasets procesados.

### 7. Auditor de datos

Espera ver:

- trazabilidad completa;
- reportes de calidad;
- cambios de estado;
- evidencia de ejecuciones;
- historial de acciones sensibles;
- consistencia de datos y cumplimiento.

### 8. Super admin / admin de sistema

Espera ver:

- usuarios;
- roles;
- permisos;
- seguridad;
- estado de Redis;
- estado de ETL;
- administracion global;
- accesos a modulos de analytics y gobierno.

## Linea visual solicitada para Stitch

Queremos conservar una sensacion cercana a **Expedia / Hotels / Trivago**, especialmente en:

- buscador superior claro;
- filtros laterales o superiores;
- cards de hoteles con jerarquia visual;
- uso de fotos, precio, rating y badges;
- experiencia limpia, profesional y confiable.

Pero el sistema tambien debe incorporar un lenguaje de producto B2B/B2B2C para sus zonas autenticadas:

- sidebars por rol;
- dashboards con tablas, metricas, estados y actividad;
- vistas de monitoreo;
- densidad de informacion razonable;
- modulos operativos claros;
- estética moderna pero utilitaria.

### Tono visual deseado

- profesional;
- limpio;
- moderno;
- confiable;
- orientado a producto real;
- mezcla entre travel-tech y analytics platform.

### Lo que NO debe hacer Stitch

- no convertir todo en un dashboard tecnico frio;
- no convertir todo en una landing page de marketing;
- no diseñar una OTA de reservas completa ignorando ETL y gobierno de datos;
- no mezclar todos los roles en una sola pantalla;
- no inventar funcionalidades muy alejadas del stack actual;
- no entregar pantallas genericas de IA sin contexto real del dominio hotelero;
- no usar placeholders abstractos que podrian pertenecer a cualquier SaaS;
- no abusar de cards vacias, graficos decorativos, paneles sin datos utiles o layouts demasiado conceptuales;
- no proponer interfaces tipo "AI workspace", "copilot dashboard" o "prompt studio" si no responden a un caso real del producto.

## Instruccion explicita contra diseño generico de IA

Stitch debe **omitir patrones visuales genericos generados por IA** cuando esos patrones no representen el negocio real. En concreto:

- no usar dashboards universales que sirvan igual para fintech, salud, CRM o cualquier otra industria;
- no usar pantallas con bloques lorem, metricas inventadas o widgets sin relacion con hoteles, reservas, revenue o ETL;
- no usar una estetica de concepto futurista solo porque "se ve a IA";
- no priorizar efectos visuales sobre flujos reales de usuario;
- no crear interfaces excesivamente vacias, abstractas o de portfolio.

Cada pantalla debe verse como parte de un producto hotelero-operativo real, con contenido, acciones y jerarquia propias de:

- busqueda hotelera;
- comparacion de propiedades;
- reservas;
- partner central;
- inventario;
- revenue;
- analytics;
- calidad de datos;
- auditoria;
- seguridad y permisos.

Si Stitch necesita decidir entre un diseño llamativo pero generico y un diseño mas especifico del dominio, debe elegir siempre el diseño mas especifico del dominio.

## Instruccion clave para la IA

La IA debe diseñar una experiencia donde cada usuario vea informacion coherente con su rol. El sistema debe parecer una sola plataforma, pero con vistas claramente diferenciadas para:

- experiencia publica / cliente;
- partner hotelero;
- revenue;
- analitica;
- administracion de datos;
- seguridad del sistema.

## Plantillas que se le deben pedir a Stitch

Pedirle que genere **15 plantillas base** consistentes entre si:

1. Home / buscador principal estilo Expedia.
2. Resultados de busqueda de hoteles.
3. Detalle de hotel.
4. Comparador de hoteles.
5. Nueva solicitud de reserva.
6. Estado o detalle de reserva.
7. Dashboard de cliente con historial.
8. Dashboard de hotel partner.
9. Perfil / contenido de propiedad hotelera.
10. Inventario y disponibilidad por calendario.
11. Dashboard de revenue y promociones.
12. Analytics de conversion e ingresos.
13. Centro ETL y calidad de datos.
14. Administracion de usuarios, roles y permisos.
15. Vista de auditoria, trazabilidad y estado del sistema.

## Prioridad de diseño

Si Stitch necesita priorizar, el orden recomendado es:

1. Busqueda y resultados estilo Expedia.
2. Detalle y comparacion de hoteles.
3. Dashboard partner.
4. Revenue y analytics.
5. ETL / calidad / auditoria.
6. Seguridad y administracion.

## Instruccion de consistencia

Todas las plantillas deben compartir:

- mismo sistema de diseño;
- misma familia visual;
- mismos patrones de navegacion;
- mismos componentes base;
- consistencia entre zona publica y zona privada;
- lenguaje visual suficientemente flexible para distintos roles.

## Recomendacion de componentes

Stitch puede apoyarse en:

- top search bar tipo OTA;
- cards de hotel;
- chips y filtros;
- sidebars por rol;
- tablas de datos;
- metric cards;
- status badges;
- timelines de auditoria;
- paneles de calidad;
- comparativos y charts;
- calendarios para disponibilidad y tarifas.

## Documentacion revisada para construir este brief

Se leyeron como referencia estos documentos del proyecto:

- `docs/empresa.md`
- `docs/objetivos.md`
- `docs/estado_general_proyecto.md`
- `docs/roles.md`
- `docs/ta02_casos_uso.md`
- `docs/ga03/casos_uso_03.md`
- `docs/ga03/casos_uso_ga03.md`
- `docs/ga03/modulo_cliente_viajero.md`
- `docs/ga03/modulo_hotel_partner.md`
- `docs/ga03/usuarios_demo_ga03.md`
- `docs/ga03/control_acceso_roles_ga03.md`
- `docs/ga03/modelo_seguridad_implementado.md`
- `docs/ga03/redis_integracion_real.md`
- `docs/ga03/docker_compose_base.md`
- `docs/frontend/frontend_migration_status.md`
- `docker-compose.yml`

## Nota sobre documentos desactualizados

Parte de la documentacion de casos de uso esta desactualizada respecto al estado actual, porque el proyecto ya agrego:

- login basico;
- usuarios demo;
- roles;
- permisos;
- seguridad;
- modulo cliente/viajero;
- modulo partner;
- revenue;
- Redis;
- Docker Compose;
- frontend Angular en migracion.

Por eso Stitch debe tomar como verdad el **estado actual ampliado**, no una lectura antigua donde el sistema era solo ETL + dashboard.

## Prompt sugerido para Google Stitch

Diseña 15 plantillas coherentes para una plataforma llamada HotelData Analytics. La plataforma combina experiencia de busqueda hotelera inspirada en Expedia con modulos de analitica, revenue, partner central, gobierno de datos, ETL, seguridad y auditoria. Mantén una linea visual cercana a Expedia/Hotels/Trivago en la zona publica y una linea profesional tipo SaaS operacional en la zona autenticada. Los usuarios incluyen cliente, hotel partner, gerente de hotel, revenue manager, marketing hotelero, operador de datos, auditor de datos y super admin. Cada rol debe ver informacion distinta y coherente con su contexto. El sistema consume un dataset de eventos y reservas de Expedia llevado a PocketBase y procesado por ETL con Python, Airflow, MongoDB, Redis, Docker y frontend Angular/FastAPI. Genera plantillas para busqueda, resultados, detalle, comparacion, reservas, partner, inventario, revenue, analytics, ETL, calidad, seguridad y auditoria, manteniendo un mismo sistema de diseño y una experiencia creible de producto real. Evita por completo diseños genericos de IA, dashboards universales sin contexto, layouts abstractos, heroes vacios y componentes que podrian pertenecer a cualquier industria. Cada pantalla debe parecer hecha especificamente para una plataforma hotelera-operativa real.
