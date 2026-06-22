# Especificación: Filtros y Comparación de Hoteles

**Versión**: 1.0 | **Estado**: Draft

**Casos de uso TAF06**: CU-O03 (Filtrar y comparar hoteles)

## 1. Objetivo

Permitir que el cliente refine resultados de búsqueda mediante filtros (precio, rating, amenities, tipo de habitación) y compare hoteles lado a lado para tomar una decisión informada.

## 2. Contexto

Una vez que el cliente ve resultados de búsqueda, necesita filtrar por rango de precio, calificación mínima, amenities (WiFi, piscina, desayuno) y comparar hasta 3 hoteles simultáneamente.

## 3. Actores

- Cliente / Viajero

## 4-13. (Secciones abreviadas - completar en iteración)

| ID | Resumen |
|----|---------|
| RF-001 | Filtrar por rango de precio (mín-máx) |
| RF-002 | Filtrar por rating mínimo (1-5) |
| RF-003 | Filtrar por amenities (WiFi, piscina, desayuno incluido) |
| RF-004 | Comparar hasta 3 hoteles en vista lado a lado |
| RF-005 | GET /hotels/compare con IDs de hoteles a comparar |

**Escenario**: Cliente aplica filtro de precio $50-150 y rating ≥ 4, luego compara 2 hoteles.

**Criterios**: CA-001: Filtro por precio funciona; CA-002: Filtro por rating funciona; CA-003: Vista comparativa muestra diferencias lado a lado.

**Dependencias**: dim_hotels, hotel_content_pages, hotel_images, amenities

**Fuera de alcance**: Comparación con hoteles de otros sistemas (OTAs)
