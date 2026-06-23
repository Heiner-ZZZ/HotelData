HotelData 
TA 06 – Estrategia y Visión Arquitectónica 
Construcción del Software - Sexto semestre 
Ingeniería de Software 
 
Sistema: HotelData 
Arquitectura base: Angular + FastAPI + MongoDB + Redis + Docker + Airflow 
Volumen analítico actual: 600000 registros hoteleros procesados en modelo Fact-Dim. 
 
 
Tabla de contenido 
- 
1. Desarrollo empresarial aplicado a HotelData 
- 
2. Descripción de la empresa, misión y visión 
- 
3. Niveles organizacionales 
- 
4. Objetivo estratégico general 
- 
5. Mapa estratégico Balanced Scorecard 
- 
6. Perspectivas del mapa estratégico 
- 
7. Cuadro resumen del Balanced Scorecard 
- 
8. Plan de acción estratégico 
- 
9. Sistema propuesto, actores y módulos 
- 
10. Objetivos estratégicos, tácticos y operativos 
- 
11. Catálogo general de casos de uso 
- 
12. Diagrama textual de casos de uso 
- 
13. Matriz de aporte del sistema a los niveles organizacionales 
- 
14. Visión arquitectónica 
- 
15. Agregaciones usadas en el sistema 
- 
16. Matriz por casos de uso estratégicos 
- 
17. Matriz por casos de uso tácticos 
- 
18. Matriz por casos de uso operativos 
- 
19. Técnicas de IA y Machine Learning aplicables 
- 
20. Técnicas de Deep Learning aplicables 
- 
21. Relación entre registros operativos y reportes gerenciales 
- 
22. Ejemplo completo de trazabilidad 
- 
23. Resumen final por nivel organizacional 
 
 
1. Desarrollo empresarial aplicado a HotelData 
El desarrollo empresarial en HotelData se entiende como la capacidad de crecer, competir, innovar y sostenerse 
mediante una plataforma hotelera digital. La empresa no se limita a registrar reservas: integra adquisición digital 
de clientes, gestión operativa hotelera, revenue management, seguridad por roles, analítica sobre datos masivos y 
trazabilidad funcional. Esta estrategia permite que la organización conecte sus decisiones de largo plazo con 
procesos tácticos y acciones operativas verificables dentro del sistema. 
La documentación se desarrolla sobre los tres niveles organizacionales: estratégico, táctico y operativo. El nivel 
estratégico define la expansión, la competitividad y los objetivos globales. El nivel táctico organiza módulos y 
procesos por área: marketing, revenue, operaciones, datos y sistemas. El nivel operativo ejecuta acciones concretas 
dentro de la aplicación: búsqueda, reserva, edición de perfil hotelero, carga ETL, auditoría, reseñas, facturación, 
login JWT y reportes. 
- 
El sistema responde hacia dónde quiere ir la empresa: expansión digital internacional y ventaja competitiva basada 
en datos. 
- 
Define qué áreas deben mejorar: captación, reservas, gestión hotelera, APIs, infraestructura, seguridad, datos y BI. 
- 
Establece cómo se medirá el avance: KPIs de conversión, CAC, revenue, disponibilidad, registros procesados, 
calidad y auditoría. 
2. Descripción de la empresa, misión y visión 
2.1 Empresa 
HotelData es una plataforma web de gestión y analítica hotelera orientada a clientes, hoteles partner, gerentes, 
revenue managers, marketing hotelero, recepcionistas, super administración y auditores de datos. Su propuesta 
combina una aplicación Angular, servicios FastAPI, base MongoDB, Redis, Docker y Airflow para sostener una 
operación hotelera digital con análisis de datos masivos. 
Actualmente el sistema trabaja con 600000 registros hoteleros procesados y organizados mediante colecciones de 
hechos y dimensiones. Esta base permite estudiar eventos de búsqueda, reservas, clicks, precios, promociones, 
destinos, países visitantes, canales, propiedades, tarifas y calidad de datos. 
Aspecto 
Descripción 
Tecnología principal 
Qué hace 
Gestiona 
búsqueda, 
reservas, 
propiedades, 
habitaciones, 
disponibilidad, 
tarifas, 
políticas, 
amenities, 
reseñas, 
facturación/comprobantes, reportes y gobierno de datos. 
Angular, 
FastAPI, 
MongoDB, 
Redis, Docker, Airflow 
A quién sirve 
Clientes/viajeros, hoteles partner, gerentes, revenue managers, 
marketing hotelero, recepcionistas, super administración y auditores de datos 
de datos. 
JWT, 
roles, 
permisos, 
rutas 
segmentadas y navegación por rol 
Problema 
que 
resuelve 
Reduce dispersión operativa, mejora conversión digital, 
centraliza datos y permite decisiones de mercado basadas en BI. 
Modelo 
Fact-Dim, 
dashboards, 
reportes y trazabilidad 
Alcance actual 
Plataforma operativa y analítica con módulos de cliente, 
management, 
sistema, 
pipeline, 
auditoría, 
reseñas 
y 
facturación/comprobantes. 
600000 registros, endpoints JSON, 
validaciones 
y 
documentación 
técnica 
 
2.2 Misión 
Brindar una plataforma digital confiable para gestionar reservas, propiedades hoteleras, datos operativos y 
analíticos, facilitando la adquisición automatizada de clientes, la administración hotelera, la integración con 
ecosistemas externos y la toma de decisiones basada en datos. 
2.3 Visión 
Ser una plataforma hotelera digital de referencia para mercados internacionales, reconocida por su capacidad de 
escalar comercialmente, integrarse mediante APIs, mantener alta disponibilidad y convertir datos hoteleros masivos 
en ventaja competitiva para hoteles y partners. 
3. Niveles organizacionales 
HotelData se estructura en tres niveles. El nivel estratégico define el rumbo global de crecimiento y diferenciación; 
el nivel táctico convierte esa estrategia en planes por área; y el nivel operativo ejecuta las acciones diarias dentro 
de la aplicación. Los tres niveles se conectan mediante objetivos, procesos, funcionalidades, indicadores KPI y 
casos de uso. 
Nivel 
organizacional 
Responsables 
Qué define 
Horizonte 
Estratégico 
Gerencia, 
dueños, 
super 
administración 
Expansión internacional, modelo de ingresos, 
alianzas, APIs, ventaja competitiva y metas 
globales. 
Largo plazo 
Táctico 
Revenue manager, marketing 
hotelero, 
admin 
sistema, 
gerente hotel, partner 
Campañas, tarifas, integraciones, dashboards, 
roles, 
disponibilidad, 
reportes 
y 
gestión 
operativa. 
Mediano 
plazo 
Operativo 
Cliente, 
recepcionista, 
gerente 
hotel, 
auditor 
datos, 
sistema FastAPI/Airflow 
Búsquedas, reservas, login JWT, check-in/out, 
cambios de perfil, reseñas, facturación, ETL y 
auditoría. 
Corto plazo 
 
4. Objetivo estratégico general 
Impulsar la expansión internacional de HotelData mediante adquisición digital automatizada, escalabilidad 
comercial por APIs y ecosistemas, infraestructura portable de alta disponibilidad e inteligencia de negocio 
centralizada sobre datos hoteleros masivos. La empresa busca crecer reduciendo fricción comercial, integrando 
partners, manteniendo continuidad técnica y tomando decisiones basadas en 600000 registros procesados en 
MongoDB. 
5. Mapa estratégico Balanced Scorecard 
El mapa estratégico organiza los objetivos de HotelData en cuatro perspectivas conectadas. La perspectiva de 
aprendizaje, tecnología y crecimiento habilita procesos internos confiables; los procesos internos sostienen la 
experiencia de clientes y partners; y la experiencia del mercado genera resultados financieros. 
APRENDIZAJE, TECNOLOGÍA Y CRECIMIENTO 
- 
Arquitectura Angular + FastAPI + MongoDB + Redis + Docker + Airflow 
- 
Autenticación JWT y control por roles 
- 
APIs estables 
- 
Cultura de datos 
- 
600000 registros procesados 
PROCESOS INTERNOS 
- 
ETL incremental 
- 
Auditoría funcional 
- 
Gestión de propiedades 
- 
Habitaciones, disponibilidad y tarifas 
- 
Políticas, amenities, reseñas y facturación/comprobantes 
CLIENTES Y MERCADO 
- 
Captación digital 
- 
Búsqueda y reserva 
- 
Reputación online 
- 
Integración con partners 
- 
Reducción de fricción comercial 
FINANCIERA 
- 
Crecimiento de reservas 
- 
Revenue bruto 
- 
Reducción de CAC internacional 
- 
Ingresos por APIs 
- 
Optimización de precios y margen comercial 
6. Perspectivas del mapa estratégico 
A. Perspectiva Financiera 
Objetivo 
estratégico 
Indicador 
Fórmula 
Meta 
Iniciativa estratégica 
Responsable 
Incrementar 
ingresos por 
reservas 
digitales 
Revenue 
bruto 
y 
reservas 
detectadas 
SUM(reservas_brutas_usd); 
COUNT(reserva_bool=true) 
+15% 
por 
ciclo 
de 
mejora 
Optimizar 
búsqueda, 
detalle, 
promociones, 
tarifas y reserva digital. 
Gerencia 
/ 
Revenue 
Reducir costo 
de 
adquisición 
internacional 
CAC 
internacional 
Inversión digital / clientes 
adquiridos 
Reducir CAC 
por región 
Automatización 
de 
campañas, analítica de 
embudo y segmentación 
de mercados. 
Marketing / 
Growth 
Aumentar 
ingresos por 
integraciones 
MRR/ARR 
por API 
Ingresos 
recurrentes 
vía 
partners / ingresos totales 
Incrementar 
participación 
por 
integraciones 
Contratos 
API, 
documentación 
y 
consumo 
por 
partners 
externos. 
Admin 
sistema 
Mejorar 
ticket 
promedio 
Precio 
promedio 
/ 
revenue por 
reserva 
AVG(price_usd); 
revenue/reservas 
Subir 
ticket 
promedio por 
segmento 
Tarifas, 
promociones, 
cupones, 
upselling 
y 
facturación/comprobante. 
Revenue 
manager 
 
B. Perspectiva del Cliente y Mercado 
Objetivo 
estratégico 
Indicador 
Fórmula 
Meta 
Iniciativa estratégica 
Responsable 
Mejorar 
conversión del 
embudo digital 
Tasa 
de 
conversión 
Reservas detectadas / 
eventos totales x 100 
Mejora 
trimestral por 
mercado 
Búsqueda, filtros, detalle, 
comparación y solicitud de 
reserva. 
Marketing 
/ 
UX 
Mejorar 
confianza 
del 
huésped 
Tasa 
de 
reseñas 
y 
puntuación 
promedio 
AVG(calificación); 
reseñas respondidas / 
reseñas recibidas 
Reseñas 
visibles 
y 
respondidas 
Módulo 
de 
reseñas, 
moderación y respuesta. 
Marketing 
hotelero 
Reducir fricción 
de compra 
Tiempo 
de 
reserva y tasa 
de abandono 
Tiempo 
medio 
de 
solicitud; 
abandonos/eventos 
Menor 
abandono del 
flujo 
Formulario de reserva, login 
JWT, 
perfil 
y 
comprobante/facturación. 
Cliente 
/ 
Sistema 
Personalizar 
experiencia por 
mercado 
Segmentos 
de 
mayor 
conversión 
Reservas por país, 
destino y canal 
Top mercados 
identificados 
BI 
por 
dim_visitor_countries, 
dim_destinations 
y 
dim_sites. 
Analítica / BI 
 
C. Perspectiva de Procesos Internos 
Objetivo 
estratégico 
Indicador 
Fórmula 
Meta 
Iniciativa estratégica 
Responsabl
e 
Automatizar 
operación de 
reservas 
Reservas 
gestionadas 
y estados 
COUNT(booking_orders) 
por 
estado 
Trazabilida
d completa 
de reservas 
booking_orders, 
booking_guests 
y 
booking_status_histor
y. 
Gerente 
hotel 
Asegurar 
disponibilida
d e inventario 
Días 
de 
inventario 
configurado
s 
COUNT(room_inventory_calenda
r) 
Inventario 
visible por 
fecha 
Habitaciones, 
room_types, 
hotel_rooms 
y 
calendario 
de 
disponibilidad. 
Hotel 
partner 
Objetivo 
estratégico 
Indicador 
Fórmula 
Meta 
Iniciativa estratégica 
Responsabl
e 
Estandarizar 
tarifas 
y 
promociones 
Planes 
tarifarios y 
campañas 
COUNT(rate_plans), 
COUNT(promotion_campaigns) 
Tarifas 
y 
campañas 
activas 
Rate 
plans, 
hotel_rate_calendar, 
cupones 
y 
promociones. 
Revenue 
manager 
Garantizar 
trazabilidad 
funcional 
Cambios 
auditados 
COUNT(user_activity_logs 
+ 
hotel_profile_changes) 
100% 
de 
cambios 
críticos 
auditables 
Auditoría 
funcional 
desde 
FastAPI, 
historial de perfil y 
sesiones. 
Auditor 
/ 
Sistema 
 
D. Perspectiva de Aprendizaje, Tecnología y Crecimiento 
Objetivo 
estratégico 
Indicador 
Fórmula 
Meta 
Iniciativa 
estratégica 
Responsable 
Fortalecer 
arquitectura 
de software 
Servicios 
disponibles 
Servicios activos / servicios 
esperados 
Alta 
disponibilidad 
local/cloud 
Angular, 
FastAPI, 
MongoDB, 
Redis, 
Docker y Airflow. 
DevOps 
/ 
Admin 
sistema 
Mejorar 
madurez de 
APIs 
Endpoints 
documentados 
y validados 
Endpoints validados / endpoints 
totales 
Contratos API 
estables 
FastAPI, 
validadores, 
contratos frontend-
backend y pruebas. 
Desarrollo 
Aumentar 
cultura 
de 
datos 
Registros 
procesados 
COUNT(fact_hotel_reservations) 
600000 
registros 
procesados 
ETL/ELT 
incremental, 
data_quality_reports 
y modelo fact-dim. 
Auditor 
datos 
Fortalecer 
seguridad 
por rol 
Usuarios con 
rol y sesión 
trazable 
Usuarios con rol / total usuarios 
100% 
de 
usuarios con 
rol 
JWT 
auth, 
roles, 
permisos, 
user_sessions 
y 
guards. 
Super admin 
 
7. Cuadro resumen del Balanced Scorecard 
Perspectiva 
Objetivo principal 
Indicador clave 
Meta estratégica 
Financiera 
Aumentar ingresos digitales 
Revenue bruto / reservas detectadas 
+15% por ciclo de 
mejora 
Financiera 
Reducir CAC internacional 
CAC por mercado 
Reducción 
progresiva 
por región 
Cliente 
Mejorar conversión del embudo 
Tasa de conversión 
Mejora trimestral por 
mercado 
Cliente 
Fortalecer reputación online 
Puntuación promedio de reseñas 
Reseñas 
visibles 
y 
respondidas 
Procesos internos 
Automatizar reservas y estados 
booking_orders por estado 
Trazabilidad completa 
Procesos internos 
Estandarizar tarifas e inventario 
rate_plans 
/ 
room_inventory_calendar 
Datos 
operativos 
visibles 
Aprendizaje 
y 
tecnología 
Fortalecer arquitectura 
Servicios disponibles 
Alta 
disponibilidad 
local/cloud 
Aprendizaje 
y 
tecnología 
Aumentar cultura de datos 
Registros procesados 
600000 registros 
 
8. Plan de acción estratégico 
Acción 
Plazo 
Responsable 
Recurso necesario 
Resultado esperado 
Optimizar búsqueda, detalle y 
reserva digital para mejorar 
conversión 
1 mes 
Marketing 
/ 
Desarrollo 
Angular, FastAPI, métricas 
de embudo 
Mayor número de 
reservas detectadas y 
menor abandono. 
Publicar contratos JSON de 
endpoints 
principales 
y 
validarlos 
2 semanas 
Admin sistema / 
Desarrollo 
FastAPI, 
validadores, 
documentación OpenAPI 
APIs estables para 
integración 
con 
partners. 
Acción 
Plazo 
Responsable 
Recurso necesario 
Resultado esperado 
Consolidar seed operativo y 
datos reales de habitaciones, 
tarifas, 
políticas, 
reseñas 
y 
facturación 
1 mes 
Hotel partner / 
Revenue 
MongoDB, formularios de 
management, validaciones 
Módulos visibles y 
coherentes 
para 
demo y operación. 
Ejecutar pipeline Airflow para 
sostener 600000 registros y 
crecimiento incremental 
Permanente 
Auditor de Datos 
Airflow, 
MongoDB, 
data_quality_reports 
Carga 
trazable, 
calidad controlada y 
crecimiento 
del 
modelo Fact-Dim. 
Reforzar JWT, roles, permisos, 
sesiones y navegación por rol 
1 semana 
Super admin / 
Desarrollo 
JWT auth, guards Angular, 
route_permissions FastAPI 
Cero 
accesos 
no 
autorizados en rutas 
sensibles. 
Implementar 
y 
documentar 
auditoría funcional de cambios 
críticos 
2 semanas 
Auditor datos / 
FastAPI 
user_activity_logs, 
hotel_profile_changes, 
booking_status_history 
Historial verificable 
por 
usuario, 
rol, 
campo y fecha. 
Activar módulo de reseñas y 
reputación online 
1 mes 
Marketing 
hotelero 
Colecciones reviews, UI de 
reseñas, moderación 
Mayor confianza del 
huésped y datos de 
satisfacción. 
Formalizar 
comprobantes/facturación 
asociada a reservas 
1 mes 
Gerente hotel / 
Sistema 
booking_orders, 
reservation_invoices, 
payments 
Trazabilidad 
de 
cobros y respaldo 
documental. 
 
9. Sistema propuesto, actores y módulos 
9.1 Sistema propuesto 
Sistema propuesto: HotelData - Plataforma de gestión hotelera, analítica, APIs, seguridad y gobierno de datos. Su 
propósito es controlar la experiencia de cliente, reservas, propiedades, habitaciones, disponibilidad, tarifas, 
políticas, amenities, reseñas, facturación/comprobantes, reportes, indicadores, ETL, trazabilidad y crecimiento 
estratégico. 
9.2 Actores del sistema 
Actor 
Descripción y responsabilidades 
Cliente / Viajero 
Busca hoteles, filtra resultados, compara opciones, revisa detalle, solicita reservas, 
consulta 
historial, 
cancela 
reservas 
permitidas, 
registra 
reseñas 
y 
recibe 
comprobantes/facturación de reserva. 
Recepcionista 
Atiende front desk: registra reservas manuales (walk-in, telefónicas), completa check-in y 
check-out de huéspedes, genera facturas y comprobantes, registra pagos. 
Hotel Partner / Dueño 
Administra propiedades, perfiles comerciales, nombres visibles editables, habitaciones, 
disponibilidad, políticas, amenities, imágenes, tarifas y reportes de sus hoteles. 
Gerente de hotel 
Supervisa operación diaria, consulta y confirma solicitudes de reserva, actualiza inventario 
por fecha, registra bloqueos de disponibilidad, consulta reportes de revenue y mercado. 
Revenue Manager 
Configura planes tarifarios, calendarios de tarifa, reglas de precio, promociones, cupones 
y análisis de revenue por hotel, destino, canal y fecha. 
Marketing hotelero 
Gestiona campañas digitales, reputación, reseñas, contenido comercial, imágenes, 
amenities, nombres visibles y comunicación hacia huéspedes. 
Super Admin 
Administra usuarios, roles, permisos, JWT auth, rutas protegidas, monitoreo, 
configuración global, auditoría, control de acceso, consulta de historial de cambios y 
moderación de reseñas. 
Auditor de Datos 
Ejecuta y valida pipeline Airflow, revisa cargas, conteos, calidad de datos, rechazos, 
reportes técnicos, estado de servicios, auditoría funcional, sesiones, cambios de perfil, 
historial de reservas, trazabilidad y registros críticos. 
Sistema FastAPI / Airflow 
Ejecuta validaciones automáticas, ETL/ELT incremental, cálculo de métricas, generación 
de reportes, auditoría funcional, cache y endpoints JSON. 
 
9.3 Módulos principales del sistema 
Módulo 
Descripción 
Experiencia cliente 
Búsqueda, 
filtros, 
detalle, 
comparación, 
reserva, 
perfil, 
reseñas 
y 
comprobantes/facturación. 
Módulo 
Descripción 
Gestión hotelera 
Panel, reservas, check-in/out, propiedades, habitaciones, disponibilidad, políticas, 
amenities y contenido. 
Revenue y promociones 
Planes tarifarios, reglas, calendario de tarifas, campañas, cupones, pricing y revenue. 
Analítica y reportes 
Dashboard, management reports, top hoteles/destinos/países, conversiones, revenue, 
calidad y Balanced Scorecard. 
Sistema y seguridad 
Usuarios, roles, permisos, JWT, sesiones, auditoría, monitoreo, trazabilidad y navegación 
por rol. 
ETL y datos 
Airflow, 
MongoDB, 
modelo 
Fact-Dim, 
data_quality_reports, 
rejected_records, 
etl_executions y 600000 registros. 
APIs e integraciones 
Contratos FastAPI, endpoints JSON, validaciones frontend/backend y preparación para 
partners/marketplaces. 
 
10. Objetivos estratégicos, tácticos y operativos 
10.1 Objetivos estratégicos 
Código 
Objetivo estratégico 
OE1 
OE1: Penetrar mercados hoteleros digitales nacionales e internacionales mediante una plataforma web de 
búsqueda, comparación, reputación, reserva y respaldo documental que convierta eventos de navegación 
en oportunidades reales de captación de clientes. 
OE2 
OE2: Escalar comercialmente HotelData mediante servicios API, módulos de gestión hotelera y 
capacidades reutilizables que permitan operar propiedades, preparar integraciones externas y reducir la 
dependencia de procesos manuales aislados. 
OE3 
OE3: Asegurar expansión continua y disponibilidad técnica de HotelData mediante una arquitectura 
portable basada en Docker, FastAPI, Angular, MongoDB, Redis y Airflow que permita operar, validar y 
escalar servicios sin depender de configuraciones manuales dispersas. 
OE4
OE4: Consolidar inteligencia de negocio hotelera centralizada mediante MongoDB Fact-Dim, dashboards,
reportes, BI, segmentación, modelos predictivos y control de calidad para transformar datos de búsqueda
y reserva en decisiones estratégicas.
OE5
OE5: Monitorear la eficiencia operativa del hotel mediante KPIs de rotación, limpieza, mantenimiento,
ocupación y cargos adicionales para optimizar la operación diaria y la experiencia del huésped.

10.2 Objetivos tácticos
Código 
Objetivo táctico 
OT1.1 
Automatizar captación digital internacional mediante búsqueda, reserva, campañas y analítica de embudo. 
OT1.2 
Fortalecer reputación, confianza del huésped, reseñas, comprobantes y comunicación digital. 
OT2.1 
Estandarizar servicios por API, contratos JSON, seguridad JWT y documentación OpenAPI. 
OT2.2 
Integrar módulos comerciales y operativos: propiedades, habitaciones, tarifas, políticas, amenities y 
contenido. 
OT3.1 
Mantener infraestructura portable y escalable con Docker, Redis, MongoDB, Angular y FastAPI. 
OT3.2 
Automatizar procesamiento de datos, gobierno, ETL/ELT, calidad, auditoría y trazabilidad. 
OT4.1 
Consolidar analítica hotelera global mediante dashboards y reportes de management. 
OT4.2 
Aplicar BI, IA, modelos predictivos, segmentación, forecasting y detección de anomalías. 
 
10.3 Objetivos operativos 
Código 
Objetivo operativo 
OO1.1.1 
Registrar eventos de búsqueda y reserva digital con país, destino, canal, hotel, fecha y usuario. 
OO1.1.2 
Medir conversión de búsqueda, detalle, click, reserva, abandono y revenue por segmento. 
OO1.2.1 
Registrar reseñas de estancia y respuestas del hotel con moderación y trazabilidad. 
OO1.2.2 
Generar comprobantes/facturación y registro de pago asociado a la reserva. 
OO2.1.1 
Exponer endpoints JSON para hoteles, reservas, management, sistema, auth y reportes. 
OO2.1.2 
Validar JWT, sesión, permisos, rol y navegación por cada endpoint sensible. 
OO2.2.1 
Administrar perfil comercial de hotel con nombres visibles manuales y prop_id estable. 
OO2.2.2 
Conectar habitaciones, tarifas, disponibilidad, políticas, amenities e imágenes. 
OO3.1.1 
Ejecutar servicios principales con Docker y configuración reproducible. 
OO3.1.2 
Monitorear Redis, backend, contratos, health checks y estado de servicios. 
OO3.2.1 
Ejecutar pipeline Airflow para cargar, validar y actualizar 600000 registros incrementales. 
OO3.2.2 
Registrar auditoría funcional, sesiones, cambios, historial y calidad de datos. 
Código 
Objetivo operativo 
OO4.1.1 
Consultar dashboard ejecutivo con eventos, reservas, revenue, precio medio y calidad. 
OO4.1.2 
Analizar mercados, destinos, canales, países visitantes y hoteles con mayor rendimiento. 
OO4.2.1 
Proyectar demanda, revenue, conversión, ocupación y campañas por mercado. 
OO4.2.2 
Detectar anomalías, registros rechazados, caídas de conversión e inconsistencias. 
 
11. Catálogo general de casos de uso 
11.1 Casos de uso estratégicos 
Código 
Caso de uso 
Actor principal 
Objetivo 
relacionado 
CU-E01 
Consultar Balanced Scorecard HotelData 
Gerente / Super admin 
OE1-OE4 
CU-E02 
Analizar conversión digital y CAC internacional 
Marketing / Revenue 
OE1, OE4 
CU-E03 
Evaluar ingresos, consumo y madurez de integraciones 
API 
Admin sistema 
OE2 
CU-E04 
Monitorear disponibilidad global, Docker, Redis y 
servicios 
Super admin / DevOps 
OE3 
CU-E05 
Analizar mercados visitantes, destinos, canales y hoteles 
Gerente / BI 
OE1, OE4 
CU-E06 
Definir estrategia de revenue, campañas y pricing 
Revenue manager 
OE1, OE4 
CU-E07 
Evaluar calidad de datos, pipeline Airflow y registros 
rechazados 
Auditor de Datos 
OE3, OE4 
CU-E08
Generar reporte gerencial consolidado para toma de
decisiones
Gerente general
OE1-OE4
CU-E09
Monitorear eficiencia operativa del hotel
Super Admin / Gerente general
OE5

11.1.1 Matriz de Casos de Uso Estratégicos (CE)
| Código CE | Código CU | Caso de uso | Actor principal | Módulo | Objetivo | OE relacionado |
|-----------|-----------|-------------|-----------------|--------|----------|----------------|
| CE-01 | CU-E01–CU-E04 | Supervisión estratégica y operativa del sistema | Gerente / Super admin / Admin sistema | gobierno_integración | Proveer a la alta dirección visibilidad consolidada del BSC, conversión digital, consumo de API y disponibilidad técnica del sistema | OE1–OE4 |
| CE-02 | CU-E05–CU-E08 | Inteligencia de mercados y reporting ejecutivo | Gerente / Revenue manager / Auditor de Datos | datos_analítica | Consolidar el análisis de mercados, revenue, calidad de datos y reportes gerenciales para la toma de decisiones estratégicas | OE1–OE4 |
| CE-03 | CU-E09 | Monitorear eficiencia operativa del hotel | Super Admin / Gerente general | operaciones_integración | Proporcionar a la gerencia una visión consolidada de KPIs operativos: rotación, limpieza, mantenimiento, ocupación real vs disponible, cargos adicionales promedio | OE5 |

11.2 Casos de uso tácticos
Código 
Caso de uso 
Actor principal 
Objetivo 
relacionado 
CU-T01 
Gestionar campañas digitales, promociones y cupones 
Marketing hotelero / Revenue 
OE1, OE4 
CU-T02 
Gestionar contratos API, endpoints y documentación 
OpenAPI 
Admin sistema / Desarrollo 
OE2 
CU-T03 
Administrar 
perfil 
comercial 
de 
propiedad 
con 
manual_override 
Hotel partner / Marketing 
OE2 
CU-T04 
Gestionar tipos de habitación y habitaciones físicas 
Hotel partner 
OE2, OE3 
CU-T05 
Configurar 
disponibilidad, 
bloqueos 
y 
calendario 
operativo 
Gerente hotel 
OE2, OE3 
CU-T06 
Configurar planes tarifarios, rate rules y cupones 
Revenue manager 
OE1, OE4 
CU-T07 
Gestionar políticas hoteleras, cancelación y condiciones 
de uso 
Hotel partner 
OE1, OE2 
CU-T08 
Gestionar amenities, imágenes y contenido comercial 
Marketing hotelero 
OE1, OE2 
CU-T09 
Administrar usuarios, roles, permisos y navegación por 
rol 
Super admin / Admin sistema 
OE3 
CU-T10 
Consultar auditoría y trazabilidad funcional 
Auditor de Datos 
OE3 
CU-T11 
Monitorear servicios Docker, Redis, backend y contratos 
API 
Super Admin 
OE3 
CU-T12 
Ejecutar y validar pipeline Airflow sobre 600000 registros 
Auditor de Datos 
OE3, OE4 
CU-T13
Gestionar reseñas, reputación online y respuestas
Marketing hotelero
OE1
CU-T14
Gestionar rotación y limpieza de habitaciones
Gerente de hotel
OE3 (OT3.3)
CU-T15
Programar mantenimiento preventivo proactivo
Gerente de hotel
OE3 (OT3.3)

11.2.1 Matriz de Casos de Uso Tácticos (CT)
| Código CT | Código CU | Caso de uso | Actor principal | Módulo | Objetivo | OE relacionado |
|-----------|-----------|-------------|-----------------|--------|----------|----------------|
| CT-01 | CU-T01–CU-T03 | Gestión comercial, técnica y de perfil de propiedad | Marketing / Admin sistema / Hotel partner | comercial_integración | Administrar campañas, contratos API y perfil comercial de propiedades para habilitar la operación digital | OE1, OE2, OE4 |
| CT-02 | CU-T04–CU-T07 | Gestión de inventario, tarifas y políticas hoteleras | Hotel partner / Gerente hotel / Revenue manager | operaciones_tarifas | Configurar habitaciones, disponibilidad, tarifas, políticas y cancelaciones para optimizar la ocupación y el revenue | OE1–OE4 |
| CT-03 | CU-T08–CU-T13 | Gestión de contenido, usuarios, datos y monitoreo | Marketing / Super admin / Auditor de Datos | gobierno_datos | Gestionar contenido comercial, usuarios, auditoría, monitoreo de servicios, ETL y reseñas para asegurar calidad operativa | OE1–OE4 |
| CT-04 | CU-T14 | Gestionar rotación y limpieza de habitaciones | Gerente de hotel | operaciones_integración | Optimizar el tiempo de rotación entre check-out y check-in, estableciendo métricas objetivo de eficiencia de limpieza | OE3 (OT3.3) |
| CT-05 | CU-T15 | Programar mantenimiento preventivo proactivo | Gerente de hotel | operaciones_integración | Establecer plan de mantenimiento recurrente basado en histórico, estacionalidad y uso, minimizando interrupciones | OE3 (OT3.3) |

11.3 Casos de uso operativos
Código 
Caso de uso 
Actor principal 
Objetivo 
relacionado 
CU-O01 
Iniciar sesión con autenticación JWT y rol 
Todos los usuarios 
OE2, OE3 
CU-O02 
Buscar hoteles 
Cliente 
OE1 
CU-O03 
Filtrar y comparar hoteles 
Cliente 
OE1 
CU-O04 
Ver detalle de hotel 
Cliente 
OE1 
CU-O05 
Solicitar reserva 
Cliente 
OE1 
CU-O06 
Consultar mis reservas 
Cliente 
OE1 
Código 
Caso de uso 
Actor principal 
Objetivo 
relacionado 
CU-O07 
Cancelar reserva según política 
Cliente 
OE1 
CU-O08 
Registrar reserva manual 
Recepcionista 
OE1, OE2 
CU-O09 
Consultar solicitudes de reserva 
Gerente hotel 
OE2 
CU-O10 
Completar check-in 
Recepcionista 
OE2 
CU-O11 
Completar check-out 
Recepcionista 
OE2 
CU-O12 
Editar nombre comercial del hotel 
Marketing / Partner 
OE2 
CU-O13 
Consultar historial de cambios de propiedad 
Auditor de Datos / Partner 
OE3 
CU-O14 
Crear tipo de habitación 
Hotel partner 
OE2 
CU-O15 
Actualizar inventario por fecha 
Gerente hotel 
OE2 
CU-O16 
Registrar bloqueo de disponibilidad 
Gerente hotel 
OE2 
CU-O17 
Crear plan tarifario 
Revenue manager 
OE4 
CU-O18 
Configurar tarifa por fecha 
Revenue manager 
OE4 
CU-O19 
Crear promoción y cupón 
Marketing / Revenue 
OE1, OE4 
CU-O20 
Editar política hotelera 
Hotel partner 
OE2 
CU-O21 
Actualizar amenities, imágenes y contenido 
Marketing hotelero 
OE1 
CU-O22 
Registrar reseña de estancia 
Cliente 
OE1 
CU-O23 
Moderar y responder reseña 
Marketing / Super Admin 
OE1 
CU-O24 
Generar comprobante o factura de reserva 
Sistema / Recepcionista 
OE1 
CU-O25 
Registrar pago asociado a reserva 
Recepcionista 
OE1, OE2 
CU-O26 
Consultar reportes de revenue y mercado 
Gerente / Revenue 
OE4 
CU-O27 
Consultar reporte de calidad y registros rechazados 
Auditor de Datos 
OE3, OE4 
CU-O28 
Administrar cuenta, sesión y cierre seguro 
Todos los usuarios 
OE3 
CU-O29
Cambiar contraseña y actualizar perfil de usuario
Todos los usuarios
OE3
CU-O30
Consultar estado actual de habitaciones
Recepcionista / Gerente
OE3
CU-O31
Asignar tipo de habitación
Recepcionista / Gerente
OE3
CU-O32
Consultar disponibilidad por habitación
Recepcionista / Gerente
OE3
CU-O33
Gestionar amenities por tipo de habitación
Hotel partner / Marketing
OE3
CU-O34
Registrar cargos adicionales a reserva
Recepcionista / Gerente
OE3
CU-O35
Editar metadata de destino
Auditor de Datos
OE2
CU-O36
Editar nombre visible de hotel (manual_override)
Auditor de Datos / Marketing
OE2
CU-O37
Visualizar mapa mundial de destinos con hoteles
Auditor de Datos / Marketing
OE2
CU-O38
Seleccionar ubicación de destino en mapa interactivo
Auditor de Datos
OE2
CU-O39
Gestionar limpieza y rotación de habitaciones
Recepcionista / Gerente
OE3
CU-O40
Gestionar mantenimiento preventivo de habitaciones
Gerente de hotel
OE3

12. Diagrama textual de casos de uso
-- CLIENTE / VIAJERO -- 
- 
Iniciar sesión con JWT 
- 
Buscar hoteles 
- 
Filtrar y comparar hoteles 
- 
Ver detalle de hotel 
- 
Solicitar reserva 
- 
Consultar mis reservas 
- 
Cancelar reserva 
- 
Registrar reseña 
- 
Recibir comprobante/factura 
-- GESTIÓN HOTELERA -- 
- 
Consultar panel de gestión 
- 
Gestionar reservas 
- 
Completar check-in 
- 
Completar check-out 
- 
Editar perfil de propiedad 
- 
Gestionar habitaciones 
- 
Configurar disponibilidad 
- 
Editar políticas y amenities 
-- REVENUE Y MARKETING -- 
- 
Crear plan tarifario 
- 
Configurar tarifa por fecha 
- 
Crear promociones y cupones 
- 
Gestionar reseñas 
- 
Actualizar imágenes y contenido 
- 
Analizar revenue 
-- SISTEMA Y DATOS -- 
- 
Administrar usuarios y permisos 
- 
Validar JWT y roles 
- 
Consultar auditoría 
- 
Ejecutar Airflow 
- 
Validar calidad de datos 
- 
Monitorear Redis/Docker/API 
13. Matriz de aporte del sistema a los niveles organizacionales 
La siguiente matriz relaciona los objetivos estratégicos, tácticos y operativos con el proceso que apoya el sistema, su funcionalidad, el KPI y el caso de uso correspondiente. Se 
usan celdas combinadas para conservar la relación OE -> OT -> OO sin repetir texto innecesariamente. Cada fila explica de forma pormenorizada cómo HotelData aporta a lo que 
la empresa quiere lograr. 
OBJETIVO 
ESTRATÉGICO 
OBJETIVO 
TÁCTICO 
OBJETIVO 
OPERATIVO 
PROCESO QUE 
APOYA 
EL 
SISTEMA 
FUNCIONALIDAD DEL SISTEMA 
INDICADOR KPI 
CASO DE USO 
OE1: 
Penetrar 
mercados 
hoteleros 
digitales nacionales e 
internacionales 
mediante 
una 
plataforma web de 
búsqueda, 
comparación, 
reputación, reserva y 
respaldo documental 
que convierta eventos 
de 
navegación 
en 
oportunidades reales 
de 
captación 
de 
clientes. 
OT1.1: 
Automatizar 
la 
captación 
digital 
internacional 
mediante 
un 
embudo web que 
conecte 
búsqueda 
de hoteles, filtros 
comerciales, detalle 
de 
propiedad, 
comparación 
de 
alternativas 
y 
solicitud de reserva 
con 
métricas 
de 
comportamiento del 
viajero. 
OO1.1.1: 
Registrar 
eventos de búsqueda y 
reserva digital vinculados 
a hotel, destino, país 
visitante, canal, precio, 
promoción, 
fecha 
y 
composición del viaje 
para medir la intención 
real 
del 
cliente 
en 
HotelData. 
Búsqueda hotelera 
digital y registro de 
intención 
comercial 
del 
viajero. 
El sistema permite que el cliente busque 
hoteles, aplique filtros por precio, 
destino, promoción, adultos, niños y 
habitaciones, 
revise 
detalle 
de 
propiedad, 
compare 
alternativas 
y 
solicite una reserva desde la interfaz 
Angular. Los eventos quedan vinculados 
a fecha, hotel, país visitante, destino y 
canal para análisis posterior. 
Tasa de conversión, 
eventos totales, clicks, 
reservas 
detectadas, 
CAC 
por 
mercado, 
tiempo 
medio 
de 
solicitud. 
CU-O01: Iniciar sesión 
con autenticación JWT; 
CU-O02: Buscar hoteles; 
CU-O03: 
Filtrar 
y 
comparar hoteles; CU-
O04: Ver detalle de hotel; 
CU-O05: 
Solicitar 
reserva. 
OO1.1.2: 
Medir 
la 
conversión 
entre 
búsqueda, visualización 
de 
detalle, 
click, 
comparación y reserva 
detectada para identificar 
qué 
países, 
canales, 
destinos, promociones y 
rangos de precio generan 
mayor probabilidad de 
compra. 
Growth analytics y 
medición 
del 
embudo digital de 
adquisición 
hotelera. 
HotelData 
calcula 
métricas 
desde 
fact_hotel_reservations y dimensiones 
relacionadas para conocer eventos, 
clicks, reservas, promociones, precio 
promedio, revenue y comportamiento 
por mercado. Esta información permite 
decidir en qué países, canales o destinos 
conviene invertir campañas digitales. 
Conversión 
= 
reservas/eventos x 100; 
click 
rate 
= 
clicks/eventos x 100; 
revenue bruto; precio 
promedio; top países; 
top destinos. 
CU-E02: 
Analizar 
conversión digital y CAC 
internacional; 
CU-E05: 
Analizar 
mercados 
visitantes; 
CU-O26: 
Consultar 
reportes 
de 
revenue y mercado. 
OT1.2: 
Fortalecer 
la 
reputación 
y 
experiencia 
del 
huésped 
mediante 
reseñas, respuestas 
administrativas, 
políticas 
visibles, 
información 
OO1.2.1: 
Registrar 
reseñas de estancia y 
respuestas del hotel para 
convertir la opinión del 
huésped en evidencia de 
satisfacción, 
reputación 
online y mejora continua 
por propiedad. 
Gestión 
de 
reputación online y 
retroalimentación 
del huésped por 
hotel. 
La plataforma contempla que el cliente 
registre reseñas posteriores a una 
estancia o reserva, mientras marketing o 
administración 
pueden 
moderar 
y 
responder. 
Las 
reseñas 
alimentan 
indicadores de satisfacción, confianza 
del huésped, reputación y oportunidades 
de mejora en propiedades o servicios. 
Puntuación promedio 
de reseñas; tasa de 
reseñas 
respondidas; 
número de reseñas por 
hotel; 
tiempo 
de 
respuesta 
a 
reseñas 
negativas. 
CU-O22: Registrar reseña 
de 
estancia; 
CU-O23: 
Moderar 
y 
responder 
reseña; 
CU-T13: 
Gestionar 
reseñas 
y 
reputación online. 
OBJETIVO 
ESTRATÉGICO 
OBJETIVO 
TÁCTICO 
OBJETIVO 
OPERATIVO 
PROCESO QUE 
APOYA 
EL 
SISTEMA 
FUNCIONALIDAD DEL SISTEMA 
INDICADOR KPI 
CASO DE USO 
comercial del hotel 
y 
evidencias 
documentales 
asociadas 
a 
la 
reserva. 
OO1.2.2: Emitir o asociar 
comprobantes 
y 
facturación de reserva 
con pagos, cancelaciones, 
estados 
y 
trazabilidad 
para 
ofrecer 
respaldo 
documental al cliente y 
control 
financiero 
al 
hotel. 
Respaldo 
documental, 
facturación 
de 
reserva y control 
comercial 
del 
pago. 
El sistema asocia la reserva con 
comprobantes o facturas, métodos de 
pago y trazabilidad del estado. Esta 
funcionalidad fortalece la confianza del 
cliente y ofrece respaldo documental al 
hotel 
para 
pagos, 
cancelaciones, 
auditoría y reportes financieros. 
Facturas/comprobantes 
generados sin error; 
pagos 
registrados; 
reservas con respaldo 
documental; 
monto 
facturado por período. 
CU-O24: 
Generar 
comprobante o factura de 
reserva; 
CU-O25: 
Registrar pago asociado a 
reserva; 
CU-O08: 
Registrar reserva manual. 
OE2: 
Escalar 
comercialmente 
HotelData mediante 
servicios 
API, 
módulos de gestión 
hotelera 
y 
capacidades 
reutilizables 
que 
permitan 
operar 
propiedades, preparar 
integraciones 
externas y reducir la 
dependencia 
de 
procesos 
manuales 
aislados. 
OT2.1: 
Estandarizar 
los 
servicios 
del 
sistema 
mediante 
endpoints 
JSON 
documentables que 
conecten 
hoteles, 
reservas, 
management, 
reportes, 
autenticación, 
usuarios, 
propiedades, 
habitaciones, 
tarifas, políticas y 
auditoría. 
OO2.1.1: 
Exponer 
endpoints 
JSON 
documentables para que 
las funcionalidades de 
hoteles, reservas, gestión, 
reportes y administración 
puedan ser consumidas 
por Angular y futuras 
integraciones 
con 
partners, 
OTAs 
o 
sistemas externos. 
Integración 
API 
para 
consumo 
frontend, partners 
y 
ecosistemas 
hoteleros externos. 
FastAPI expone endpoints para hoteles, 
reservas, 
management, 
reportes, 
autenticación, usuarios, propiedades, 
habitaciones, 
tarifas, 
políticas 
y 
auditoría. La empresa puede preparar 
integraciones con marketplaces, OTAs, 
partners 
y 
sistemas 
externos 
sin 
reconstruir la lógica principal. 
Endpoints 
activos; 
endpoints 
validados; 
errores API; tiempo de 
respuesta; 
rutas 
documentables; 
contratos 
frontend-
backend aprobados. 
CU-T02: 
Gestionar 
contratos 
API 
y 
documentación 
OpenAPI; 
CU-E03: 
Evaluar 
ingresos 
y 
madurez de integraciones 
API. 
OO2.1.2: 
Validar 
autenticación 
JWT, 
sesión 
activa, 
rol 
principal, 
permisos 
y 
reglas de acceso por 
endpoint para proteger las 
zonas 
de 
cliente, 
management y sistema. 
Control de acceso, 
autorización 
por 
rol y seguridad de 
APIs protegidas. 
El sistema usa autenticación JWT, 
sesiones, 
roles, 
permisos, 
guards 
Angular y reglas FastAPI para proteger 
rutas de cliente, management y sistema. 
La navegación se adapta por rol para 
evitar que usuarios sin permiso vean 
módulos 
sensibles 
como 
usuarios, 
permisos, auditoría o administración 
global. 
Accesos 
no 
autorizados; 
sesiones 
activas; usuarios con 
rol; rutas protegidas; 
errores 
401/403 
esperados. 
CU-O01: Iniciar sesión 
con autenticación JWT; 
CU-O28: 
Administrar 
cuenta, sesión y cierre 
seguro; 
CU-T09: 
Administrar 
usuarios, 
roles y permisos. 
OT2.2: Integrar los 
módulos 
comerciales 
y 
operativos del hotel 
mediante gestión de 
perfil, 
contenido, 
habitaciones, 
disponibilidad, 
tarifas, 
políticas, 
OO2.2.1: Administrar el 
perfil comercial del hotel 
con nombres manuales 
editables, preservando el 
identificador técnico  , 
protegiendo los cambios 
con manual_override y 
registrando 
historial 
en hotel_profile_changes. 
Gestión 
de 
propiedad, 
enriquecimiento 
manual 
y 
trazabilidad 
del 
perfil 
comercial 
hotelero. 
El sistema mantiene prop_id como llave 
técnica 
estable 
y 
permite 
editar 
display_name, 
hotel_name 
y 
descripciones 
visibles. 
Cuando 
un 
nombre se modifica manualmente, 
manual_override 
evita 
que 
el 
enriquecimiento automático o ETL lo 
sobrescriba. Cada cambio queda en 
hotel_profile_changes. 
Cambios 
auditados; 
nombres 
manuales 
preservados; 
propiedades con perfil 
completo; 
score 
operativo 
por 
propiedad. 
CU-T03: 
Administrar 
perfil 
comercial 
de 
propiedad; 
CU-O12: 
Editar nombre comercial 
del 
hotel; 
CU-O13: 
Consultar 
historial 
de 
cambios de propiedad. 
OBJETIVO 
ESTRATÉGICO 
OBJETIVO 
TÁCTICO 
OBJETIVO 
OPERATIVO 
PROCESO QUE 
APOYA 
EL 
SISTEMA 
FUNCIONALIDAD DEL SISTEMA 
INDICADOR KPI 
CASO DE USO 
amenities, 
imágenes 
y 
promociones dentro 
del 
área 
Management. 
OO2.2.2: 
Conectar 
habitaciones, 
tarifas, 
disponibilidad, políticas y 
amenities para que cada 
hotel pueda configurar su 
oferta 
operativa 
y 
comercial 
desde 
Management con datos 
visibles 
para 
cliente, 
reportes y análisis. 
Partner Central / 
Management 
operativo 
para 
configuración 
integral de la oferta 
hotelera. 
El 
módulo 
de 
gestión 
conecta 
room_types, 
hotel_rooms, 
room_inventory_calendar, 
rate_plans, 
hotel_rate_calendar, 
hotel_policies, 
hotel_images y hotel_content_pages. 
Esto permite que un hotel partner 
configure su oferta y que la app muestre 
datos completos al cliente y a reportes. 
Habitaciones 
configuradas; días de 
inventario; 
tarifas 
activas; 
políticas 
registradas; imágenes 
disponibles; 
score 
operativo. 
CU-T04: 
Gestionar 
habitaciones; 
CU-T05: 
Configurar 
disponibilidad; CU-T06: 
Configurar tarifas; CU-
T07: Gestionar políticas; 
CU-T08: 
Gestionar 
amenities e imágenes. 
OE3: 
Asegurar 
expansión continua y 
disponibilidad 
técnica de HotelData 
mediante 
una 
arquitectura portable 
basada en Docker, 
FastAPI, 
Angular, 
MongoDB, Redis y 
Airflow que permita 
operar, 
validar 
y 
escalar servicios sin 
depender 
de 
configuraciones 
manuales dispersas. 
OT3.1: 
Mantener 
una infraestructura 
portable y escalable 
que 
separe 
frontend, backend, 
base 
de 
datos, 
caché, servicios de 
soporte y ejecución 
técnica 
para 
facilitar despliegue 
local, validación y 
futura 
expansión 
cloud. 
OO3.1.1: 
Ejecutar 
backend y servicios de 
soporte en Docker para 
mantener 
un 
entorno 
reproducible 
donde 
FastAPI, 
Redis, 
MongoDB local/cloud y 
frontend Angular puedan 
operar 
de 
forma 
coordinada. 
Despliegue, 
operación técnica y 
portabilidad 
del 
entorno 
de 
ejecución. 
HotelData se mantiene sobre una 
arquitectura portable con Docker para 
backend 
y 
servicios 
de 
soporte, 
MongoDB local/cloud, Redis y frontend 
Angular. 
Esta 
estructura 
permite 
reproducir 
el 
entorno, 
facilitar 
despliegues y preparar una futura 
expansión cloud. 
Uptime; 
tiempo 
de 
arranque; 
servicios 
activos; 
tiempo 
de 
despliegue; errores por 
contenedor. 
CU-E04: 
Monitorear 
disponibilidad global y 
servicios; 
CU-T11: 
Monitorear 
Docker, 
Redis y backend. 
OO3.1.2: Mantener Redis 
como 
componente 
de 
soporte 
para 
estado 
técnico, 
monitoreo 
de 
disponibilidad, 
preparación de caché y 
validación de servicios 
dentro 
del 
stack 
de 
HotelData. 
Monitoreo técnico, 
soporte 
de 
rendimiento 
y 
preparación 
de 
caché 
para 
endpoints críticos. 
Redis funciona como componente de 
soporte para estado técnico, caché 
futura, monitoreo de disponibilidad y 
preparación de endpoints cacheables. Su 
estado se valida desde sistema para 
asegurar que el stack responda aunque 
algunos servicios no estén en uso 
intensivo. 
Redis status; latencia 
de respuesta; endpoints 
cacheables; 
health 
checks; 
errores 
técnicos. 
CU-T11: 
Monitorear 
servicios Docker, Redis y 
backend; 
CU-E04: 
Monitorear 
disponibilidad global. 
OT3.2: 
Automatizar 
el 
procesamiento 
y 
gobierno de datos 
mediante pipelines 
ETL 
capaces 
de 
cargar 
registros 
hoteleros, actualizar 
dimensiones, 
OO3.2.1: 
Ejecutar 
el 
pipeline ETL con Airflow 
para extraer, transformar, 
validar y cargar datos 
hoteleros en MongoDB, 
manteniendo soporte para 
crecimiento incremental, 
nuevas dimensiones y 
reportes de calidad. 
Orquestación ETL, 
carga incremental 
y 
control 
de 
calidad de datos 
hoteleros. 
Airflow 
orquesta 
la 
extracción, 
transformación, validación y carga de 
datos hacia MongoDB. El pipeline debe 
soportar 
crecimiento 
incremental, 
nuevos IDs de dimensiones, reportes de 
calidad, 
rejected_records, 
data_quality_reports y etl_executions. 
Registros 
cargados; 
duración 
DAG; 
registros 
rechazados; 
nuevas 
dimensiones; 
cobertura 
fact-dim; 
errores 
de 
transformación. 
CU-T12: 
Ejecutar 
y 
validar pipeline Airflow 
sobre 600000 registros; 
CU-E07: Evaluar calidad 
de datos y pipeline; CU-
O27: Consultar reporte de 
calidad. 
OBJETIVO 
ESTRATÉGICO 
OBJETIVO 
TÁCTICO 
OBJETIVO 
OPERATIVO 
PROCESO QUE 
APOYA 
EL 
SISTEMA 
FUNCIONALIDAD DEL SISTEMA 
INDICADOR KPI 
CASO DE USO 
controlar 
calidad, 
registrar rechazos y 
conservar bitácoras 
de ejecución. 
OO3.2.2: 
Registrar 
auditoría, 
sesiones 
y 
trazabilidad mediante 
user_activity_logs,  
user_sessions, 
hotel_profile_changes,  
booking_status_history, 
data_quality_reports y 
etl_executions. 
Gobierno de datos, 
auditoría funcional 
y 
evidencia 
de 
operaciones 
críticas. 
FastAPI registra acciones importantes en 
user_activity_logs, 
hotel_profile_changes, 
booking_status_history, user_sessions, 
data_quality_reports y etl_executions. 
Esto permite conocer quién hizo qué, 
cuándo, desde qué rol y sobre qué 
entidad. 
Cobertura de auditoría; 
cambios por usuario; 
sesiones 
activas; 
historial por propiedad; 
operaciones 
críticas 
auditadas. 
CU-T10: 
Consultar 
auditoría y trazabilidad; 
CU-O13: 
Consultar 
historial de cambios; CU-
O28: Administrar sesión 
y cierre seguro. 
OE4: 
Consolidar 
inteligencia 
de 
negocio 
hotelera 
centralizada mediante 
MongoDB Fact-Dim, 
dashboards, reportes, 
BI, 
segmentación, 
modelos predictivos y 
control de calidad 
para 
transformar 
datos de búsqueda y 
reserva en decisiones 
estratégicas. 
OT4.1: Consolidar 
analítica 
hotelera 
global 
mediante 
dashboards 
ejecutivos 
y 
reportes 
de 
Management 
que 
combinen eventos, 
reservas, 
clicks, 
revenue, 
precio 
promedio, 
promociones, 
calidad 
y 
desempeño 
por 
mercado. 
OO4.1.1: 
Consultar 
dashboard ejecutivo y 
management reports para 
visualizar 
eventos 
cargados, 
reservas 
detectadas, 
clicks, 
revenue, 
precio 
promedio, promociones, 
calidad, top hoteles, top 
destinos 
y 
países 
visitantes. 
BI 
y 
reporting 
ejecutivo 
para 
seguimiento 
gerencial 
de 
mercado, revenue 
y operación. 
Management Overview, reportes y 
dashboards muestran eventos, reservas, 
clicks, 
revenue, 
precio 
promedio, 
campañas, calidad, top hoteles, top 
destinos, 
países 
visitantes, 
disponibilidad y conteos de colecciones 
operativas. 
Eventos, 
reservas, 
revenue, precio medio, 
promociones, calidad, 
top 
hoteles, 
top 
destinos, top países. 
CU-E01: 
Consultar 
Balanced Scorecard; CU-
E08: 
Generar 
reporte 
gerencial; 
CU-O26: 
Consultar 
reportes 
de 
revenue y mercado. 
OO4.1.2: 
Analizar 
mercados, 
destinos, 
canales y hoteles usando  
dim_visitor_countries, 
dim_destinations,  
dim_sites y  
dim_hotels para 
identificar oportunidades 
de expansión, pricing y 
campañas. 
Inteligencia 
de 
mercado por país 
visitante, destino, 
canal y propiedad 
hotelera. 
Las dimensiones dim_visitor_countries, 
dim_destinations, 
dim_sites 
y 
dim_hotels 
permiten 
segmentar 
la 
información por mercado visitante, 
destino buscado, canal de origen y 
propiedad. 
Esto 
ayuda 
a 
decidir 
campañas, precios, disponibilidad y 
expansión. 
Top 
mercados; 
conversión por país; 
revenue por destino; 
precio promedio por 
canal; 
hoteles 
con 
mayor rendimiento. 
CU-E05: 
Analizar 
mercados 
visitantes 
y 
destinos; 
CU-E06: 
Definir 
estrategia 
de 
revenue; 
CU-O26: 
Consultar reportes. 
OT4.2: Aplicar BI, 
IA 
y 
modelos 
predictivos 
para 
anticipar demanda, 
revenue, 
conversión, 
ocupación, 
rendimiento 
por 
campaña y riesgos 
derivados 
de 
OO4.2.1: 
Proyectar 
demanda, 
revenue 
y 
conversión a partir de 
fechas, 
destinos, 
ocupación, 
precios, 
promociones 
y 
comportamiento histórico 
de búsqueda para apoyar 
decisiones de tarifas y 
campañas. 
Revenue planning, 
forecasting 
y 
planificación 
predictiva 
de 
demanda hotelera. 
El sistema puede aplicar forecasting 
sobre 
fechas, 
destinos, 
ocupación, 
precios, promociones y comportamiento 
de búsqueda. Estas proyecciones ayudan 
a planificar campañas, tarifas, inventario 
y expansión por país o destino. 
Demanda 
prevista; 
ocupación 
estimada; 
revenue 
proyectado; 
variación 
de 
conversión; 
rendimiento 
por 
campaña. 
CU-E06: 
Definir 
estrategia de revenue y 
promociones; 
CU-T06: 
Configurar 
planes 
tarifarios; CU-O17/O18: 
Crear planes y tarifas. 
OBJETIVO 
ESTRATÉGICO 
OBJETIVO 
TÁCTICO 
OBJETIVO 
OPERATIVO 
PROCESO QUE 
APOYA 
EL 
SISTEMA 
FUNCIONALIDAD DEL SISTEMA 
INDICADOR KPI 
CASO DE USO 
anomalías 
o 
problemas 
de 
calidad. 
OO4.2.2: 
Detectar 
anomalías y problemas de 
calidad relacionados con 
registros 
rechazados, 
caídas 
de 
conversión, 
datos 
incompletos, 
precios atípicos, errores 
de 
carga 
o 
cambios 
inesperados del mercado. 
Calidad de datos, 
gestión de riesgos 
analíticos y mejora 
continua 
del 
modelo hotelero. 
La 
plataforma 
analiza 
registros 
rechazados, 
caídas 
anormales 
de 
conversión, datos incompletos, precios 
atípicos, errores de carga y cambios 
inesperados en comportamiento de 
mercado. 
Esto 
permite 
acciones 
correctivas técnicas y comerciales. 
Anomalías detectadas; 
registros 
rechazados; 
calidad 
del 
dataset; 
caídas de conversión; 
campos incompletos. 
CU-E07: Evaluar calidad 
de datos y pipeline; CU-
O27: Consultar reporte de 
calidad 
y 
registros 
rechazados. 
 
14. Visión arquitectónica 
A continuación se relacionan los niveles organizacionales de HotelData con los casos de uso del sistema, indicando 
qué técnicas analíticas o de inteligencia artificial podrían aplicarse, qué modelos Fact-Dim se usarían y qué registros 
o reportes alimentan cada proceso. 
14.1 Enfoque general por nivel organizacional

| Nivel organizacional | Tipo de decisión | Técnicas principales | Tipo de datos usados |
|---|---|---|---|
| Estratégico | Decisiones gerenciales y de largo plazo sobre expansión, revenue, alianzas, mercados y ventaja competitiva | BI, agregaciones, predicción, detección de tendencias, ML, segmentación global y simulación de escenarios | Datos históricos consolidados de reservas, clicks, revenue, destinos, países, canales, campañas, calidad y auditoría |
| Táctico | Planeación por áreas y control mensual/semanal de marketing, revenue, propiedades, sistemas y datos | Segmentación, pronósticos, alertas, análisis de promociones, optimización de tarifas, monitoreo API y control de inventario | Datos agrupados por hotel, destino, país visitante, canal, fecha, campaña, rol, propiedad, tarifa y estado de reserva |
| Operativo | Ejecución diaria de búsqueda, reserva, check-in/out, edición de perfil, carga ETL, reseñas, facturación y auditoría | Reglas de negocio, validaciones automáticas, alertas operativas, recomendaciones simples, registros transaccionales y trazabilidad | Datos en tiempo real de reservas, sesiones, pagos, reseñas, cambios de perfil, habitaciones, disponibilidad y logs |

14.2 Modelo analítico general del sistema
El sistema mantiene dos grandes capas: operación hotelera y modelo analítico. La operación diaria registra acciones 
concretas; el modelo Fact-Dim consolida esas acciones para análisis táctico y estratégico. 
Sistema operativo HotelData 
Registra búsquedas, reservas, check-in/out, perfiles, reseñas, pagos, facturación, inventario, tarifas, auditoría y 
cargas ETL 
↓ 
Base operacional en MongoDB 
Colecciones transaccionales y de gestión diaria 
↓ 
Data Warehouse / Modelo Fact-Dim en MongoDB 
Hechos y dimensiones para análisis de 600000 registros 
↓ 
Reportes, tableros, BI, Machine Learning, predicciones y trazabilidad 
 
14.3 Tablas de hechos principales

Las tablas Fact almacenan eventos medibles. En HotelData se documentan con prefijo `Fact_` para mantener el enfoque analítico y diferenciar hechos de dimensiones o catálogos.

| Tabla Fact | Qué mide | Ejemplos de métricas |
|---|---|---|
| `Fact_Hotel_Reservations` | Eventos de búsqueda, click, reserva y revenue del dataset Expedia/HotelData | eventos, reservas, clicks, price_usd, reservas_brutas_usd, conversion_rate, promotion_flag |
| `Fact_Hotel_Events` | Eventos históricos de interacción hotelera usados como capa de compatibilidad analítica | eventos cargados, hotel, destino, país visitante, canal, fecha |
| `Fact_Booking_Orders` | Solicitudes y órdenes de reserva operativas dentro de la aplicación | estado de reserva, fecha, hotel, usuario, monto, fuente |
| `Fact_Booking_Status_History` | Cambios de estado de reservas, cancelaciones, check-in y check-out | estado anterior, estado nuevo, usuario, fecha, razón |
| `Fact_Room_Inventory_Calendar` | Inventario disponible por fecha, hotel y tipo de habitación | inventario total, inventario disponible, bloqueos, ocupación |
| `Fact_Hotel_Rate_Calendar` | Tarifas por fecha, hotel y plan tarifario | precio por noche, vigencia, tarifa activa, variación por fecha |
| `Fact_Promotion_Campaigns` | Campañas, promociones y cupones activos para adquisición y revenue | descuento, uso de cupón, campaña, vigencia, conversión |
| `Fact_Reservation_Invoices` | Comprobantes o facturas asociadas a reservas y pagos | subtotal, impuestos, total, estado de comprobante, fecha emisión |
| `Fact_Reservation_Payments` | Pagos asociados a reservas y confirmaciones | monto pagado, método de pago, estado, fecha, referencia |
| `Fact_Reviews` | Reseñas de huéspedes y respuestas del hotel | calificación, comentario, estado de moderación, respuesta, tiempo de respuesta |
| `Fact_User_Activity_Logs` | Actividad de usuarios, acciones críticas, rutas y módulos accedidos | usuario, rol, acción, módulo, entidad, fecha, ip |
| `Fact_Hotel_Profile_Changes` | Historial de cambios manuales en perfil comercial de hoteles | campo, valor anterior, valor nuevo, usuario, fecha, prop_id |
| `Fact_Data_Quality_Reports` | Reportes de calidad de datos generados por ejecución ETL | total registros, aceptados, rechazados, completitud, errores |
| `Fact_ETL_Executions` | Ejecuciones del pipeline Airflow/ETL y su estado | execution_id, duración, estado, filas procesadas, errores |

14.4 Dimensiones principales

| Dimensión | Uso |
|---|---|
| `Dim_Time` | date_key, año, mes, día, hora, semana y estacionalidad |
| `Dim_Hotel` | prop_id, nombre visible, rating, review score, país, marca, ubicación y manual_override |
| `Dim_Destination` | srch_destination_id, nombre visible, etiqueta de destino y región comercial |
| `Dim_Visitor_Country` | visitor_location_country_id, país/mercado visitante y etiqueta comercial |
| `Dim_Channel_Site` | site_id, canal, site_name, site_display_name y fuente de búsqueda |
| `Dim_Occupancy_Profile` | adultos, niños, habitaciones y perfil de ocupación |
| `Dim_Stay_Length_Category` | categoría de duración de estancia: corta, media o larga |
| `Dim_Booking_Window_Category` | anticipación de reserva: last minute, corto, medio o largo plazo |
| `Dim_Price_Category` | categoría de precio: bajo, medio, alto o premium |
| `Dim_Promotion` | estado de promoción, campaña, cupón y descuento aplicado |
| `Dim_Click_Status` | evento con click o sin click |
| `Dim_Reservation_Status` | evento con reserva detectada o sin reserva |
| `Dim_User_Role` | super_admin, recepcionista, hotel_partner, gerente_hotel, revenue_manager, marketing, auditor_datos |
| `Dim_Room_Type` | tipo de habitación, capacidad, hotel, estado y configuración |
| `Dim_Rate_Plan` | plan tarifario, regla, precio base, vigencia y hotel |
 
14.5 Técnicas usadas por nivel organizacional 
A. Nivel estratégico 
Técnica 
Uso en HotelData 
Agregaciones BI 
Eventos, reservas, revenue, precio promedio, conversión, top mercados, top 
destinos y top hoteles. 
Machine 
Learning 
predictivo 
Pronosticar demanda hotelera, conversión por destino, revenue por temporada y 
riesgo de caída de reservas. 
Técnica 
Uso en HotelData 
Detección de anomalías 
Identificar cambios bruscos en revenue, registros rechazados, caída de conversión 
o precios atípicos por hotel/destino. 
Segmentación de mercados 
Clasificar países visitantes, canales, destinos y hoteles con mayor potencial de 
adquisición. 
Modelos de recomendación 
Sugerir campañas, promociones, tarifas o mercados prioritarios según 
comportamiento histórico. 
Dashboards estratégicos 
Balanced Scorecard, management overview, revenue, calidad de datos y reportes 
ejecutivos. 
 
B. Nivel táctico 
Técnica 
Uso en HotelData 
Agregaciones por área 
Reservas por hotel, tarifas por fecha, campañas por estado, habitaciones por 
disponibilidad y auditoría por módulo. 
Forecasting 
Predecir demanda por temporada, destino, canal, tipo de habitación y fechas de 
mayor búsqueda. 
Clasificación 
de 
clientes/mercados 
Detectar segmentos con mayor probabilidad de reserva, abandono o recompra. 
Alertas inteligentes 
Avisar sobre bajo inventario, ausencia de tarifas, problemas de calidad, errores 
API o servicios caídos. 
Análisis de promociones 
Medir qué campaña, cupón o descuento genera más reservas, clicks y revenue. 
Optimización 
de 
inventario/tarifa 
Definir inventario visible, precios por fecha, disponibilidad bloqueada y planes 
tarifarios activos. 
 
C. Nivel operativo 
Técnica 
Uso en HotelData 
Reglas de negocio 
No permitir completar check-in/check-out sin reserva válida, no editar prop_id 
técnico, no sobrescribir manual_override. 
Validaciones automáticas 
Evitar IDs inválidos, duplicados, campos obligatorios vacíos, errores de pago y 
rutas sin permiso. 
Alertas operativas 
Avisar falta de políticas, habitaciones, imágenes, tarifas, errores de API, 
rejected_records o servicios no disponibles. 
Recomendaciones simples 
Sugerir promociones, tarifa base, disponibilidad o perfil comercial según datos 
existentes. 
Deep Learning opcional 
Clasificación de imágenes hoteleras, OCR de comprobantes, análisis visual de 
habitaciones o sentimiento en reseñas. 
Registros transaccionales 
Reservas, pagos, reseñas, facturación, perfiles, cambios, sesiones, logs, 
habitaciones y tarifas. 
 
15. Agregaciones usadas en el sistema 
Agregación 
Fórmula o cálculo 
Uso 
Eventos totales 
COUNT(Fact_Hotel_Reservations) 
Medir volumen de datos procesados y 
actividad general. 
Reservas detectadas 
COUNT(reserva_bool=true) 
Medir conversión y crecimiento de 
reservas. 
Clicks 
COUNT(click_bool=true) 
Evaluar interés del usuario sobre 
hoteles. 
Tasa de conversión 
Reservas detectadas / eventos totales x 100 Analizar efectividad del embudo 
digital. 
Click rate 
Clicks / eventos totales x 100 
Medir interacción previa a reserva. 
Revenue bruto 
SUM(reservas_brutas_usd) 
Control 
financiero 
y 
revenue 
management. 
Agregación 
Fórmula o cálculo 
Uso 
Precio promedio 
AVG(price_usd) 
Comparar tarifas por hotel, destino o 
fecha. 
Top hoteles por revenue 
SUM(revenue) GROUP BY prop_id 
Priorizar 
propiedades 
de 
alto 
rendimiento. 
Top destinos 
COUNT(reservas/eventos) GROUP BY 
srch_destination_id 
Detectar destinos con mayor demanda. 
Top países visitantes 
COUNT(eventos) 
GROUP 
BY 
visitor_location_country_id 
Identificar mercados internacionales. 
Campañas activas 
COUNT(promotion_campaigns) 
Controlar marketing y promociones. 
Calidad de datos 
Aceptados, rechazados, completitud y 
errores por ejecución 
Gobierno de datos y control de 
pipeline. 
Cobertura de auditoría 
Operaciones auditadas / operaciones 
críticas x 100 
Trazabilidad y seguridad. 
Uptime/servicios activos 
Servicios activos / servicios esperados x 
100 
Disponibilidad técnica. 
 
16. Matriz por casos de uso estratégicos 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-E01 
Consultar 
Balanced 
Scorecard 
HotelData 
BI, agregaciones, semáforos, 
comparación temporal, análisis 
ejecutivo y lectura de KPIs. 
Fact_Hotel_Reservations, 
Fact_Data_Quality_Reports, 
Fact_ETL_Executions, 
Fact_User_Activity_Logs, 
Dim_Time, 
Dim_Hotel, 
Dim_Destination, 
Dim_Channel_Site. 
Dashboard 
Balanced 
Scorecard, resumen ejecutivo, 
KPIs 
financieros, 
clientes, 
procesos y tecnología. 
eventos, 
reservas, 
clicks, 
revenue, promociones, calidad, 
sesiones, roles y ejecución ETL. 
CU-E02 
Analizar 
conversión digital y CAC 
internacional 
Embudo digital, métricas de 
adquisición, segmentación por 
mercado y análisis de abandono. 
Fact_Hotel_Reservations, 
Fact_Promotion_Campaigns, 
Dim_Visitor_Country, Dim_Destination, 
Dim_Channel_Site, Dim_Time. 
Reporte de conversión, CAC, 
click rate, reservas por país y 
destino. 
eventos de búsqueda, clicks, 
reservas, promociones, países, 
canales y fechas. 
CU-E03 Evaluar ingresos, 
consumo y madurez de 
integraciones API 
Agregaciones de consumo API, 
control de endpoints, validación 
de contratos y análisis de 
partners. 
Fact_User_Activity_Logs, 
Fact_Booking_Orders, 
Fact_Reservation_Payments, 
Dim_User_Role, Dim_Channel_Site. 
Reporte 
de 
integraciones, 
errores 
API, 
endpoints 
consumidos 
y 
potencial 
MRR/ARR. 
logs de API, usuarios, rutas, 
partners, pagos, reservas e 
integraciones. 
CU-E04 
Monitorear 
disponibilidad 
global, 
Docker, Redis y servicios 
Monitoreo de infraestructura, 
health checks, análisis de uptime 
y detección de fallos. 
Fact_User_Activity_Logs, 
Fact_ETL_Executions, 
Fact_Data_Quality_Reports, Dim_Time. 
Reporte 
de 
disponibilidad, 
estado 
Redis, 
backend, 
frontend, Docker y servicios 
críticos. 
logs técnicos, health checks, 
tiempos de respuesta y estado de 
contenedores. 
CU-E05 Analizar mercados 
visitantes, destinos, canales 
y hoteles 
BI geográfico, segmentación de 
mercados, 
ranking, 
análisis 
comparativo 
y 
mapas 
de 
demanda. 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Visitor_Country, 
Dim_Channel_Site, Dim_Time. 
Reporte de mercados, top 
países, top destinos, canales y 
propiedades 
con 
mayor 
rendimiento. 
prop_id, destino, país visitante, 
site_id, 
fecha, 
revenue 
y 
conversión. 
CU-E06 Definir estrategia 
de revenue, campañas y 
pricing 
Revenue 
management, 
simulación, forecasting, análisis 
de promociones y comparación 
por fecha. 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Time, Dim_Price_Category. 
Reporte de pricing, campañas, 
cupones, revenue y precio 
promedio. 
tarifas, 
campañas, 
precios, 
reservas, descuentos, cupones y 
fechas. 
CU-E07 Evaluar calidad de 
datos, pipeline Airflow y 
registros rechazados 
Gobierno de datos, validación de 
esquema, control de cobertura 
fact-dim y detección de errores. 
Fact_Data_Quality_Reports, 
Fact_ETL_Executions, 
Fact_Hotel_Reservations, Dim_Time. 
Reporte 
de 
calidad, 
rejected_records, cobertura de 
llaves, duración del DAG y 
errores. 
ejecuciones 
ETL, 
registros 
procesados, 
rechazados, 
completitud y dimensiones. 
CU-E08 Generar reporte 
gerencial consolidado 
BI 
ejecutivo, 
agregaciones, 
exportación, 
resumen 
por 
perspectiva 
y 
análisis 
comparativo. 
Todas las Fact principales con Dim_Time, 
Dim_Hotel, 
Dim_Destination, 
Dim_Channel_Site, Dim_User_Role. 
Reporte gerencial final con 
indicadores 
estratégicos, 
tácticos y operativos. 
datos consolidados del sistema, 
auditoría, 
reservas, 
revenue, 
calidad, campañas y usuarios. 
 
17. Matriz por casos de uso tácticos 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-T01 
Gestionar 
campañas 
digitales, 
promociones y cupones 
Segmentación, 
medición 
de 
conversión, análisis de cupón y 
campañas A/B. 
Fact_Promotion_Campaigns, 
Fact_Hotel_Reservations, 
Fact_Reservation_Payments, Dim_Time, 
Dim_Channel_Site. 
Reporte 
de 
campañas, 
cupones, descuentos, reservas 
generadas y revenue por 
promoción. 
campaign_id, 
coupon_code, 
promotion_flag, reservas, pagos, 
fechas y canales. 
CU-T02 
Gestionar 
contratos 
API 
y 
documentación OpenAPI 
Control de contratos, validación 
de 
endpoints, 
pruebas 
de 
integración y monitoreo de 
errores. 
Fact_User_Activity_Logs, 
Fact_ETL_Executions, Dim_User_Role, 
Dim_Channel_Site. 
Reporte de endpoints, rutas 
consumidas, errores, latencia 
y 
validaciones 
frontend-
backend. 
rutas 
API, 
logs, 
respuestas 
HTTP, 
sesiones, 
roles 
y 
servicios. 
CU-T03 Administrar perfil 
comercial de propiedad con 
manual_override 
Auditoría de cambios, reglas de 
preservación, 
control 
de 
nombres 
manuales 
y 
enriquecimiento display. 
Fact_Hotel_Profile_Changes, 
Fact_User_Activity_Logs, Dim_Hotel. 
Reporte de cambios de perfil, 
nombres manuales, usuario 
responsable y fecha. 
prop_id, 
display_name, 
old_value, 
new_value, 
changed_by, updated_at. 
CU-T04 Gestionar tipos de 
habitación y habitaciones 
físicas 
Control de inventario base, 
configuración 
operativa 
y 
validación de capacidad. 
Fact_Room_Inventory_Calendar, 
Dim_Room_Type, Dim_Hotel. 
Reporte 
de 
habitaciones 
configuradas, capacidad y 
estado por hotel. 
room_type_id, 
hotel_rooms, 
capacidad, prop_id y estado. 
CU-T05 
Configurar 
disponibilidad, bloqueos y 
calendario 
Reglas de negocio, alertas de 
disponibilidad, calendario y 
control de bloqueos. 
Fact_Room_Inventory_Calendar, 
Fact_Booking_Orders, Dim_Room_Type, 
Dim_Time. 
Reporte de inventario por 
fecha, 
disponibilidad 
y 
bloqueos. 
fecha, 
room_type, 
inventario 
total/disponible, blackout_dates 
y reservas. 
CU-T06 Configurar planes 
tarifarios, rate rules y 
cupones 
Revenue management, pricing 
dinámico, análisis de tarifa por 
fecha y reglas comerciales. 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, Dim_Hotel, 
Dim_Time, Dim_Price_Category. 
Reporte de tarifas, planes, 
reglas, cupones y revenue 
estimado. 
rate_plan_id, 
price, 
fecha, 
cupones, campañas y hotel. 
CU-T07 
Gestionar 
políticas 
hoteleras 
y 
cancelación 
Control normativo, reglas de 
cancelación, 
validación 
de 
condiciones y comunicación al 
cliente. 
Fact_Booking_Status_History, 
Fact_Booking_Orders, 
Dim_Hotel, 
Dim_Reservation_Status. 
Reporte 
de 
políticas 
configuradas y cancelaciones 
por tipo. 
políticas, reservas canceladas, 
estado, prop_id, usuario y fecha. 
CU-T08 
Gestionar 
amenities, 
imágenes 
y 
contenido comercial 
Clasificación 
de 
contenido, 
completitud 
de 
perfil, 
enriquecimiento 
manual 
y 
control de calidad visual. 
Fact_Hotel_Profile_Changes, Dim_Hotel, 
Dim_Room_Type. 
Reporte 
de 
contenido, 
imágenes, amenities y score 
operativo. 
hotel_content_pages, 
hotel_images, facilities, profile 
changes. 
CU-T09 
Administrar 
usuarios, roles, permisos y 
navegación por rol 
RBAC, 
validación 
JWT, 
guards, 
segregación 
de 
funciones y control de acceso. 
Fact_User_Activity_Logs, 
Dim_User_Role. 
Reporte de usuarios, roles, 
permisos, 
accesos 
no 
autorizados y sesiones. 
users, 
roles, 
permissions, 
role_permissions, user_sessions. 
CU-T10 
Consultar 
auditoría 
y 
trazabilidad 
funcional 
Auditoría funcional, historial de 
cambios, 
trazabilidad 
por 
usuario, módulo y entidad. 
Fact_User_Activity_Logs, 
Fact_Hotel_Profile_Changes, 
Fact_Booking_Status_History, 
Dim_User_Role. 
Reporte de auditoría, cambios 
críticos, 
historial 
por 
propiedad y sesión. 
logs, cambios de perfil, reservas, 
estado, usuario, rol y fecha. 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-T11 
Monitorear 
servicios Docker, Redis, 
backend y contratos API 
Health checks, monitoreo de 
disponibilidad, 
análisis 
de 
errores y estado técnico. 
Fact_User_Activity_Logs, 
Fact_ETL_Executions, Dim_Time. 
Reporte de monitoreo técnico, 
estado Redis, backend y 
validadores. 
logs de servicio, status endpoints, 
validaciones y errores. 
CU-T12 Ejecutar y validar 
pipeline 
Airflow 
sobre 
600000 registros 
ETL incremental, validación de 
cobertura, 
data 
quality, 
rejected_records y control de 
ejecuciones. 
Fact_ETL_Executions, 
Fact_Data_Quality_Reports, 
Fact_Hotel_Reservations, Dim_Time. 
Reporte de pipeline, calidad, 
registros 
procesados 
y 
rechazados. 
execution_id, 
rows, 
status, 
rejected_records, cobertura fact-
dim. 
CU-T13 Gestionar reseñas, 
reputación 
online 
y 
respuestas 
Análisis 
de 
satisfacción, 
moderación, 
respuesta, 
clasificación de sentimiento 
opcional. 
Fact_Reviews, Dim_Hotel, Dim_Time, 
Dim_User_Role. 
Reporte 
de 
reseñas, 
puntuación 
promedio, 
respuestas y reputación. 
review_id, score, comentario, 
respuesta, prop_id y usuario. 
 
18. Matriz por casos de uso operativos 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-O01 Iniciar sesión 
con autenticación JWT y 
rol 
Validación JWT, control de 
sesión, 
rol, 
permisos, 
cookies/tokens, trazabilidad de 
acceso. 
Fact_User_Activity_Logs, 
Dim_User_Role, Dim_Time 
Reporte de sesiones, accesos, 
usuarios con rol y seguridad. 
users, 
roles, 
permissions, 
user_sessions, activity logs. 
CU-O02 Buscar hoteles 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O03 
Filtrar 
y 
comparar hoteles 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O04 Ver detalle de 
hotel 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O05 Solicitar reserva 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O06 Consultar mis 
reservas 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O07 Cancelar reserva 
según política 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-O08 Registrar reserva 
manual 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O09 
Consultar 
solicitudes de reserva 
Reglas de reserva, validaciones 
de flujo, agregaciones operativas 
y análisis de embudo. 
Fact_Booking_Orders, 
Fact_Hotel_Reservations, 
Dim_Hotel, 
Dim_Destination, Dim_Time 
Reporte 
de 
solicitudes, 
reservas, 
cancelaciones 
y 
conversión. 
booking_orders, booking_guests, 
reservation status, prop_id, fecha. 
CU-O10 
Completar 
check-in 
Reglas operativas de check-
in/out, control de disponibilidad 
y estados. 
Fact_Booking_Status_History, 
Fact_Booking_Orders, 
Fact_Room_Inventory_Calendar, 
Dim_Room_Type 
Reporte de operación diaria, 
check-ins, 
check-outs 
y 
disponibilidad. 
booking_status_history, 
inventory, room_types, reservas. 
CU-O11 
Completar 
check-out 
Reglas operativas de check-
in/out, control de disponibilidad 
y estados. 
Fact_Booking_Status_History, 
Fact_Booking_Orders, 
Fact_Room_Inventory_Calendar, 
Dim_Room_Type 
Reporte de operación diaria, 
check-ins, 
check-outs 
y 
disponibilidad. 
booking_status_history, 
inventory, room_types, reservas. 
CU-O12 Editar nombre 
comercial del hotel 
Auditoría de cambios, validación 
de 
perfil, 
historial, 
manual_override y control de 
contenido. 
Fact_Hotel_Profile_Changes, 
Fact_User_Activity_Logs, Dim_Hotel 
Reporte de perfil, contenido, 
políticas, 
imágenes 
y 
cambios. 
hotel_profile_changes, 
hotel_policies, 
hotel_images, 
content_pages. 
CU-O13 
Consultar 
historial de cambios de 
propiedad 
Auditoría de cambios, validación 
de 
perfil, 
historial, 
manual_override y control de 
contenido. 
Fact_Hotel_Profile_Changes, 
Fact_User_Activity_Logs, Dim_Hotel 
Reporte de perfil, contenido, 
políticas, 
imágenes 
y 
cambios. 
hotel_profile_changes, 
hotel_policies, 
hotel_images, 
content_pages. 
CU-O14 Crear tipo de 
habitación 
Validaciones 
de 
inventario, 
calendario, pricing, promociones 
y reglas de revenue. 
Fact_Room_Inventory_Calendar, 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, Dim_Hotel, 
Dim_Time 
Reporte 
de 
habitaciones, 
tarifas, 
promociones 
y 
calendario. 
room_types, 
inventory, 
rate_plans, hotel_rate_calendar, 
coupons. 
CU-O15 
Actualizar 
inventario por fecha 
Reglas operativas de check-
in/out, control de disponibilidad 
y estados. 
Fact_Booking_Status_History, 
Fact_Booking_Orders, 
Fact_Room_Inventory_Calendar, 
Dim_Room_Type 
Reporte de operación diaria, 
check-ins, 
check-outs 
y 
disponibilidad. 
booking_status_history, 
inventory, room_types, reservas. 
CU-O16 
Registrar 
bloqueo de disponibilidad 
Reglas operativas de check-
in/out, control de disponibilidad 
y estados. 
Fact_Booking_Status_History, 
Fact_Booking_Orders, 
Fact_Room_Inventory_Calendar, 
Dim_Room_Type 
Reporte de operación diaria, 
check-ins, 
check-outs 
y 
disponibilidad. 
booking_status_history, 
inventory, room_types, reservas. 
CU-O17 
Crear 
plan 
tarifario 
Validaciones 
de 
inventario, 
calendario, pricing, promociones 
y reglas de revenue. 
Fact_Room_Inventory_Calendar, 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, Dim_Hotel, 
Dim_Time 
Reporte 
de 
habitaciones, 
tarifas, 
promociones 
y 
calendario. 
room_types, 
inventory, 
rate_plans, hotel_rate_calendar, 
coupons. 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-O18 Configurar tarifa 
por fecha 
Validaciones 
de 
inventario, 
calendario, pricing, promociones 
y reglas de revenue. 
Fact_Room_Inventory_Calendar, 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, Dim_Hotel, 
Dim_Time 
Reporte 
de 
habitaciones, 
tarifas, 
promociones 
y 
calendario. 
room_types, 
inventory, 
rate_plans, hotel_rate_calendar, 
coupons. 
CU-O19 Crear promoción 
y cupón 
Validaciones 
de 
inventario, 
calendario, pricing, promociones 
y reglas de revenue. 
Fact_Room_Inventory_Calendar, 
Fact_Hotel_Rate_Calendar, 
Fact_Promotion_Campaigns, Dim_Hotel, 
Dim_Time 
Reporte 
de 
habitaciones, 
tarifas, 
promociones 
y 
calendario. 
room_types, 
inventory, 
rate_plans, hotel_rate_calendar, 
coupons. 
CU-O20 Editar política 
hotelera 
Auditoría de cambios, validación 
de 
perfil, 
historial, 
manual_override y control de 
contenido. 
Fact_Hotel_Profile_Changes, 
Fact_User_Activity_Logs, Dim_Hotel 
Reporte de perfil, contenido, 
políticas, 
imágenes 
y 
cambios. 
hotel_profile_changes, 
hotel_policies, 
hotel_images, 
content_pages. 
CU-O21 
Actualizar 
amenities, imágenes y 
contenido 
Auditoría de cambios, validación 
de 
perfil, 
historial, 
manual_override y control de 
contenido. 
Fact_Hotel_Profile_Changes, 
Fact_User_Activity_Logs, Dim_Hotel 
Reporte de perfil, contenido, 
políticas, 
imágenes 
y 
cambios. 
hotel_profile_changes, 
hotel_policies, 
hotel_images, 
content_pages. 
CU-O22 Registrar reseña 
de estancia 
Moderación, 
reputación, 
clasificación 
opcional 
de 
sentimiento y trazabilidad. 
Fact_Reviews, Dim_Hotel, Dim_Time, 
Dim_User_Role 
Reporte 
de 
reseñas, 
calificación y respuestas. 
reviews, 
respuestas, 
usuario, 
fecha y hotel. 
CU-O23 
Moderar 
y 
responder reseña 
Moderación, 
reputación, 
clasificación 
opcional 
de 
sentimiento y trazabilidad. 
Fact_Reviews, Dim_Hotel, Dim_Time, 
Dim_User_Role 
Reporte 
de 
reseñas, 
calificación y respuestas. 
reviews, 
respuestas, 
usuario, 
fecha y hotel. 
CU-O24 
Generar 
comprobante o factura de 
reserva 
Cálculo 
de 
comprobante, 
validación de pago, estado y 
respaldo documental. 
Fact_Reservation_Invoices, 
Fact_Reservation_Payments, 
Fact_Booking_Orders, Dim_Time 
Reporte de facturación, pagos 
y reservas cobradas. 
invoices, 
payments, 
booking_orders, total, estado. 
CU-O25 Registrar pago 
asociado a reserva 
Cálculo 
de 
comprobante, 
validación de pago, estado y 
respaldo documental. 
Fact_Reservation_Invoices, 
Fact_Reservation_Payments, 
Fact_Booking_Orders, Dim_Time 
Reporte de facturación, pagos 
y reservas cobradas. 
invoices, 
payments, 
booking_orders, total, estado. 
CU-O26 
Consultar 
reportes de revenue y 
mercado 
BI, 
agregaciones, 
calidad, 
rejected records y análisis de 
indicadores. 
Fact_Hotel_Reservations, 
Fact_Data_Quality_Reports, 
Fact_ETL_Executions, 
Dim_Time, 
Dim_Hotel 
Reporte de revenue, mercado, 
calidad y pipeline. 
fact_hotel_reservations, quality 
reports, etl_executions. 
CU-O27 
Consultar 
reporte 
de 
calidad 
y 
registros rechazados 
BI, 
agregaciones, 
calidad, 
rejected records y análisis de 
indicadores. 
Fact_Hotel_Reservations, 
Fact_Data_Quality_Reports, 
Fact_ETL_Executions, 
Dim_Time, 
Dim_Hotel 
Reporte de revenue, mercado, 
calidad y pipeline. 
fact_hotel_reservations, quality 
reports, etl_executions. 
Caso de uso 
Técnicas usadas 
Modelo Fact-Dim 
Reportes generados 
Registros usados 
CU-O28 
Administrar 
cuenta, sesión y cierre 
seguro 
Validación JWT, control de 
sesión, 
rol, 
permisos, 
cookies/tokens, trazabilidad de 
acceso. 
Fact_User_Activity_Logs, 
Dim_User_Role, Dim_Time 
Reporte de sesiones, accesos, 
usuarios con rol y seguridad. 
users, 
roles, 
permissions, 
user_sessions, activity logs. 
CU-O29 
Cambiar 
contraseña y actualizar 
perfil de usuario 
Validación JWT, control de 
sesión, 
rol, 
permisos, 
cookies/tokens, trazabilidad de 
acceso. 
Fact_User_Activity_Logs, 
Dim_User_Role, Dim_Time 
Reporte de sesiones, accesos, 
usuarios con rol y seguridad. 
users, 
roles, 
permissions, 
user_sessions, activity logs. 
 
19. Técnicas de IA y Machine Learning aplicables 
A. Segmentación de clientes y mercados 
Técnica 
Aplicación en HotelData 
Clustering 
Agrupar países visitantes, destinos, hoteles y clientes según conversión, precio 
promedio y revenue. 
RFM adaptado 
Clasificar clientes o mercados por recencia, frecuencia de búsqueda/reserva y 
monto/revenue. 
Árboles de decisión 
Identificar factores que más influyen en reserva: precio, destino, rating, 
promoción o canal. 
 
B. Predicción de demanda y revenue 
Técnica 
Aplicación en HotelData 
Forecasting temporal 
Predecir demanda por fecha, destino, país, hotel y canal. 
Regresión 
Estimar revenue y precio esperado según temporada, promoción, rating y 
comportamiento histórico. 
Modelos de conversión 
Calcular probabilidad de reserva a partir de clicks, precio, destino, adultos, 
niños y rooms. 
 
C. Detección de anomalías 
Técnica 
Aplicación en HotelData 
Anomaly detection 
Detectar precios atípicos, caídas de conversión, picos de rechazos o errores de 
pipeline. 
Alertas por umbral 
Avisar si rejected_records sube, si un servicio cae o si una propiedad pierde 
score operativo. 
Comparación histórica 
Identificar desviaciones respecto a comportamiento por fecha, mercado o 
destino. 
 
D. Recomendaciones 
Técnica 
Aplicación en HotelData 
Recomendación de hoteles 
Sugerir hoteles por precio, destino, rating, promociones y comportamiento de 
búsqueda. 
Recomendación de campañas 
Sugerir promociones o cupones para mercados con alta intención y baja 
conversión. 
Recomendación de tarifas 
Sugerir ajustes de precio según demanda, disponibilidad y revenue histórico. 
 
20. Técnicas de Deep Learning aplicables 
El Deep Learning no es obligatorio para la etapa actual, pero puede incorporarse si el sistema amplía el uso de 
imágenes, documentos, reseñas y comprobantes. Se plantea como una capacidad futura coherente con la estrategia 
de crecimiento. 
Técnica Deep Learning 
Uso posible 
Caso 
de 
uso 
relacionado 
OCR con redes neuronales 
Leer comprobantes, facturas, documentos de pago o 
reservas externas. 
CU-O24, CU-O25 
Clasificación de imágenes 
Clasificar imágenes de hoteles, habitaciones, 
amenities y contenido comercial. 
CU-T08, CU-O21 
Análisis de sentimiento 
Interpretar comentarios de reseñas para detectar 
satisfacción, quejas y oportunidades. 
CU-O22, CU-O23, CU-
T13 
Técnica Deep Learning 
Uso posible 
Caso 
de 
uso 
relacionado 
Detección visual de calidad 
Revisar si una imagen hotelera es borrosa, 
duplicada o no corresponde a la propiedad. 
CU-T08 
Modelos de lenguaje 
Resumir reseñas, explicar KPIs, generar respuestas 
sugeridas y documentar reportes. 
CU-E08, CU-T13 
 
21. Relación entre registros operativos y reportes gerenciales 
Registro operativo 
Búsqueda, reserva, reseña, pago, factura, cambio de perfil, inventario, tarifa, sesión, auditoría y carga ETL 
↓ 
Agregación 
Eventos por mercado, reservas por hotel, revenue por fecha, reseñas por propiedad, calidad por ejecución 
↓ 
Modelo Fact-Dim 
Fact_Hotel_Reservations + Dim_Hotel + Dim_Destination + Dim_Visitor_Country + Dim_Channel_Site + 
Dim_Time 
↓ 
Reporte táctico o estratégico 
Balanced Scorecard, Management Overview, Revenue Reports, Calidad de Datos, Auditoría 
↓ 
Decisión 
Campaña, pricing, integración API, mejora de propiedad, control de calidad o expansión a mercado 
internacional 
 
22. Ejemplo completo de trazabilidad 
Elemento 
Detalle 
Objetivo estratégico 
OE4: Consolidar inteligencia de negocio hotelera centralizada mediante MongoDB Fact-
Dim, dashboards, reportes, BI, segmentación, modelos predictivos y control de calidad 
para transformar datos de búsqueda y reserva en decisiones estratégicas. 
Objetivo táctico 
OT4.1: Consolidar analítica hotelera global mediante dashboards ejecutivos y 
reportes de Management que combinen eventos, reservas, clicks, revenue, precio 
promedio, promociones, calidad y desempeño por mercado. 
Objetivo operativo 
OO4.1.1: Consultar dashboard ejecutivo y management reports para visualizar 
eventos cargados, reservas detectadas, clicks, revenue, precio promedio, 
promociones, calidad, top hoteles, top destinos y países visitantes. 
Proceso que apoya 
BI y reporting ejecutivo para gerencia, revenue, marketing y auditoría. 
Funcionalidad del sistema Management Overview muestra eventos, reservas, revenue, precio promedio, 
promociones, calidad, hoteles, destinos, países y colecciones operativas. 
Indicadores KPI 
Eventos totales, reservas detectadas, conversion rate, revenue bruto, precio 
promedio, rejected_records y completitud. 
Casos de uso relacionados CU-E01 Consultar Balanced Scorecard; CU-E08 Generar reporte gerencial; CU-
O26 Consultar reportes de revenue y mercado. 
Modelo Fact-Dim usado 
Fact_Hotel_Reservations, 
Fact_Data_Quality_Reports, 
Dim_Hotel, 
Dim_Destination, Dim_Visitor_Country, Dim_Channel_Site, Dim_Time. 
Registros usados 
600000 registros procesados, reservas, clicks, precios, países, destinos, canales, 
reportes de calidad y ejecuciones ETL. 
Técnicas aplicables 
BI, agregaciones, segmentación, forecasting, detección de anomalías y dashboard 
ejecutivo. 
 
23. Resumen final por nivel organizacional 
Nivel 
Casos 
de 
uso 
principales 
Técnicas recomendadas 
Resultado esperado 
Estratégico 
CU-E01 a CU-E08 
BI, ML predictivo, agregaciones, 
segmentación 
de 
mercados, 
simulación y dashboards. 
Mejor toma de decisiones, 
expansión 
internacional, 
revenue optimizado y ventaja 
competitiva basada en datos. 
Táctico 
CU-T01 a CU-T13 
Forecasting, 
análisis 
de 
promociones, control de APIs, 
auditoría, monitoreo, optimización 
de tarifas e inventario. 
Mejor planificación por área, 
control de módulos, APIs 
integrables 
y 
operación 
comercial escalable. 
Operativo 
CU-O01 a CU-O29 
Reglas de negocio, validaciones, 
alertas, registros transaccionales, 
JWT y trazabilidad funcional. 
Mejor ejecución diaria, reservas 
controladas, perfiles auditables, 
reseñas, pagos, facturación y 
seguridad por rol. 
 
 
