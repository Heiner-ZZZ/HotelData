# Especificación: Detalle de Hotel

**Versión**: 1.0 | **Estado**: Draft

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
| RF-001 | Mostrar galería de imágenes del hotel |
| RF-002 | Mostrar nombre, descripción, rating, dirección |
| RF-003 | Mostrar lista de amenities con iconos |
| RF-004 | Mostrar políticas de cancelación, check-in/out, mascotas, niños |
| RF-005 | Mostrar tarifas por tipo de habitación con disponibilidad |
| RF-006 | Mostrar reseñas de huéspedes con puntuación promedio |
| RF-007 | GET /api/hotels/{prop_id} devuelve todos los datos |

**Escenarios**: Cliente ve detalle con 8 imágenes, amenities listadas, tarifas desde $80/noche, rating 4.2, reseñas recientes.

**Criterios**: CA-001: Datos básicos se muestran correctamente; CA-002: Imágenes cargan; CA-003: Tarifas visibles por tipo habitación.

**Dependencias**: dim_hotels, hotel_content_pages, hotel_images, hotel_policies, reviews, fact_reviews

**Fuera de alcance**: Tour virtual 360°, video del hotel
