# Especificación: Filtros y Comparación de Hoteles

**Versión**: 2.0 | **Estado**: Implementado | **Última actualización**: 2026-06-22

**Casos de uso TAF06**: CU-O03 (Filtrar y comparar hoteles)

## 1. Objetivo

Permitir que el cliente refine resultados de búsqueda mediante filtros (precio, rating, amenities) y compare hoteles lado a lado para tomar una decisión informada.

## 2. Contexto

Una vez que el cliente ve resultados de búsqueda, necesita filtrar por rango de precio, calificación mínima, amenities (WiFi, piscina, desayuno) y comparar hasta 3 hoteles simultáneamente.

## 3. Actores

- Cliente / Viajero (público, no requiere autenticación)

## 4. Requisitos funcionales

| ID | Requisito |
|----|-----------|
| RF-001 | El sistema debe permitir filtrar por rango de precio (price_min, price_max) |
| RF-002 | El sistema debe permitir filtrar por rating mínimo (star_rating 1-5) |
| RF-003 | El sistema debe permitir filtrar por amenities (búsqueda de texto en amenities_text) |
| RF-004 | El sistema debe permitir comparar hasta 3 hoteles en vista lado a lado |
| RF-005 | El sistema debe exponer GET /api/hotels/compare con IDs de hoteles a comparar |
| RF-006 | La comparación debe incluir datos operacionales: tarifas (si hay fechas), tipos de habitación, amenities, políticas |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Endpoint de comparación debe responder en menos de 2 segundos para 3 hoteles |
| RNF-002 | Endpoint público (no requiere autenticación) |
| RNF-003 | La vista de comparación debe ser responsiva (tabla se desplaza horizontalmente en móvil) |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | Máximo 3 hoteles en comparación simultánea |
| RN-002 | Si se proporcionan fechas, se muestran tarifas por noche y total estimado |
| RN-003 | Los filtros de precio, rating y amenities aplican en la búsqueda (GET /api/hotels/availability) |

## 7. Entradas

| Dato | Tipo | Endpoint |
|------|------|----------|
| prop_id | int[] (múltiple) | GET /api/hotels/compare?prop_id=1&prop_id=2 |
| check_in | string (YYYY-MM-DD) | GET /api/hotels/compare?check_in=2026-07-15 |
| check_out | string (YYYY-MM-DD) | GET /api/hotels/compare?check_out=2026-07-20 |
| adults | int (default=1) | GET /api/hotels/compare?adults=2 |
| children | int (default=0) | GET /api/hotels/compare?children=1 |

## 8. Salidas

| Escenario | Respuesta |
|-----------|-----------|
| Comparación con resultados | 200 + items con datos de cada hotel |
| Sin prop_ids | 200 + items vacío (items: []) |

### Formato de respuesta:
```json
{
  "items": [
    {
      "prop_id": 1,
      "hotel_name": "Hotel A",
      "display_name": "Hotel A Madrid",
      "prop_starrating": 4.0,
      "prop_review_score": 8.5,
      "image_url": "/static/hotels/1/main.jpg",
      "amenities_text": "wifi, piscina, gimnasio",
      "room_types": [
        {
          "room_type_id": "RT-1-estandar",
          "name": "Estándar",
          "max_adults": 2,
          "max_children": 1,
          "base_capacity": 2,
          "description": "..."
        }
      ],
      "policies": { "check_in": "15:00", "check_out": "12:00" },
      "min_nightly_rate": 89.50,
      "min_nightly_rate_label": "$89.50",
      "total_estimated": 447.50,
      "total_estimated_label": "$447.50"
    }
  ]
}
```

## 9. Escenarios

### Escenario 1: Comparar 2 hoteles
```gherkin
Dado que el cliente está viendo resultados de búsqueda
Y hace clic en "Comparar" en 2 hoteles diferentes
Cuando el sistema carga GET /api/hotels/compare?prop_id=1&prop_id=2
Entonces muestra una tabla lado a lado con nombre, imagen, estrellas, rating
Y si hay fechas, muestra precio por noche y total estimado
Y muestra amenities, tipos de habitación y políticas
```

### Escenario 2: Sin hoteles seleccionados
```gherkin
Dado que el cliente accede a /hotels/compare sin parámetros
Cuando el sistema carga la página
Entonces muestra mensaje "Selecciona hoteles para comparar"
```

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Filtro por precio funciona en GET /api/hotels/availability (price_min, price_max) |
| CA-002 | Filtro por rating funciona en GET /api/hotels/availability (star_rating) |
| CA-003 | Filtro por amenities funciona en GET /api/hotels/availability (amenities) |
| CA-004 | GET /api/hotels/compare devuelve hasta 3 hoteles con datos enriquecidos |
| CA-005 | La comparación incluye tarifas cuando se proporcionan fechas |
| CA-006 | La tabla de comparación muestra diferencias lado a lado |
| CA-007 | Se puede quitar un hotel de la comparación |
| CA-008 | Se puede añadir un hotel si hay menos de 3 |

## 11. Restricciones

- Endpoint público: `/api/hotels/compare` (no requiere auth, en PUBLIC_PREFIXES)
- Fechas en formato ISO 8601 (YYYY-MM-DD)
- Máximo 3 hoteles en comparación
- Las tarifas se obtienen de hotel_rate_calendar (no en tiempo real)

## 12. Dependencias

- `server/src/app/modules/hotels/service/compare.py` — compare_hotels_with_availability()
- `server/src/app/modules/hotels/routes.py` — GET /api/hotels/compare
- `dim_hotels` — Datos maestros de hoteles
- `hotel_images` — Imágenes de propiedad
- `hotel_content_pages` — Texto de amenities
- `room_types` — Tipos de habitación por hotel
- `hotel_policies` — Políticas del hotel
- `hotel_rate_calendar` — Tarifas para el rango de fechas
- `frontend/.../hotel-compare/` — Componente Angular de comparativa

## 13. Implementaciones adicionales

### Filtros de precio, rating y amenities en búsqueda
| ID | Requisito |
|----|-----------|
| RF-007 | El sistema debe exponer price_min, price_max, star_rating, amenities en GET /api/hotels/availability |

### Vista de comparación en frontend
| ID | Requisito |
|----|-----------|
| RF-008 | El frontend debe mostrar tabla lado a lado con datos de cada hotel |
| RF-009 | El frontend debe permitir quitar hoteles de la comparación |
| RF-010 | El frontend debe enlazar a la búsqueda para añadir más hoteles |

## 14. Fuera de alcance (implementable, merece spec propio)

- Comparación con hoteles de otros sistemas (OTAs)
- CHAT BOT para sugerir hoteles similares según preferencias
- Personalización de filtros basada en preferencias del usuario
- Comparación de precios en tiempo real (conectado a motor de pricing)
- Transparencia de políticas de cancelación y reembolso en la comparación
- GANs para generar imágenes de habitaciones según descripción
- Búsqueda por coordenadas geográficas (mapa) — spec dedicado
- Comparación de hoteles con diferentes opciones de desayuno, cancelación, mascotas, etc. — spec dedicado
- Los filtros de amenities podrían ser más complejos (checkboxes, categorías) — spec dedicado
- IMG de habitaciones generadas por IA según descripción — spec dedicado

→ Ver `ideas-para-specs-dedicados.md` en la raíz del proyecto para detalles.

## 15. Nota

Items de "Comparación de hoteles con diferentes opciones de [X]" generados por IA fueron descartados. La vista de comparación muestra los datos disponibles de cada hotel en una tabla genérica lado a lado, sin necesidad de modelar cada variante de política o servicio como filtro de comparación.
