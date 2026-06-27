# Especificación: Detalle de Hotel

**Versión**: 2.0 | **Estado**: Implementado

**Casos de uso TAF06**: CU-O04 (Ver detalle de hotel)

## 1. Objetivo

Mostrar al cliente la información completa de una propiedad hotelera: galería de imágenes, descripción, amenities, políticas, tarifas por tipo de habitación, reseñas de huéspedes y mapa de ubicación.

## 2. Contexto

Después de buscar y filtrar, el cliente selecciona un hotel para ver su información completa antes de decidir reservar. Esta página es crítica para la conversión.

## 3. Actores

- Cliente / Viajero

## 4-13. Resumen

| ID | Descripción |
|----|-------------|
| RF-001 | Mostrar galería de imágenes del hotel (hotel_images) |
| RF-002 | Mostrar nombre, descripción, rating, dirección, highlights |
| RF-003 | Mostrar lista de amenities con tags (desde amenities_text de hotel_content_pages) |
| RF-004 | Mostrar políticas de cancelación, check-in/out, mascotas, niños (hotel_policies) |
| RF-005 | Mostrar tarifas por tipo de habitación desde hotel_rate_calendar |
| RF-006 | Mostrar reseñas de huéspedes con puntuación (top 5 recientes desde reviews) |
| RF-007 | Mostrar KPIs analíticos (precio promedio, reservas, clicks, eventos, tasa de conversión) |
| RF-008 | Mostrar tablas de destinos, países visitantes y canales principales |
| RF-009 | GET /api/hotels/{prop_id} devuelve todos los datos enriquecidos |

**Escenarios**: Cliente ve detalle con galería horizontal, descripción, amenities como tags, KPIs, tarifas por fecha, tipos de habitación, reseñas recientes y políticas.

**Criterios**: CA-001: Datos básicos se muestran correctamente; CA-002: Imágenes cargan en carrusel horizontal; CA-003: Tarifas visibles por fecha y plan; CA-004: Reseñas ordenadas por fecha descendente (top 5).

**Dependencias**: dim_hotels, hotel_content_pages, hotel_images, hotel_policies, reviews, room_types, hotel_rate_calendar, fact_[active]

**Fuera de alcance**: 
- Tour virtual 360° o video del hotel
- Integración con Google Maps para mapa de ubicación
- Recomendaciones de hoteles similares o cercanos
- Envío de solicitudes de reserva desde la página de detalle
- Ganancias de afiliados o comisiones por reservas
- Transacciones de pago o procesamiento de reservas
- Un sistema de mensajería interna para contactar al hotel directamente
- Personalización de la experiencia del usuario basada en historial de búsqueda o preferencias
- Generación de itinerarios o paquetes turísticos desde la página de detalle
- Envío de notificaciones push o correos electrónicos desde la página de detalle
- Integración con reseñas externas (TripAdvisor, Yelp)
- Comparación de hoteles desde la página de detalle
- Reservas directas desde la página de detalle (solo se muestra información, no se permite reservar)
- Integración con chat en vivo o soporte al cliente desde la página de detalle
- Integración con redes sociales para compartir el hotel
- Integración con programas de fidelidad o recompensas desde la página de detalle
-
