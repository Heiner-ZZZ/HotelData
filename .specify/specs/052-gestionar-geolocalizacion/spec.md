# Especificación: Gestionar Geolocalización y Metadata de Contenido

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-21

**Casos de uso TA07**: CU-O31 (Gestionar geolocalización y metadata de contenido)

## 1. Objetivo

Unificar la edición de metadata de destinos (nombre, coordenadas), la edición de nombre visible de hotel (manual_override), la visualización de mapa mundial interactivo con hoteles geolocalizados y la selección de ubicación de destino en mapa.

## 2. Contexto

Fusiona los antiguos CU-O35 (editar metadata destino), CU-O36 (editar nombre hotel), CU-O37 (visualizar mapa) y CU-O38 (seleccionar ubicación) en un único caso de uso geoespacial cohesivo.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Auditor de Datos | Edita metadata y coordenadas de destinos |
| Marketing hotelero | Edita nombres visibles y contenido |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe mostrar un mapa mundial interactivo con marcadores de destinos y hoteles | Alta |
| RF-002 | El sistema debe permitir editar nombre visible, coordenadas, país, ciudad y descripción de destinos | Alta |
| RF-003 | El sistema debe permitir editar el nombre visible del hotel activando manual_override | Alta |
| RF-004 | El sistema debe permitir seleccionar ubicación en el mapa arrastrando un marcador | Alta |
| RF-005 | El sistema debe registrar cambios en hotel_profile_changes o destinations_log | Alta |

## 5. Requisitos no funcionales

| ID | Requisito | Descripción |
|----|-----------|-------------|
| RNF-001 | Dependencia | Requiere conexión a internet para tiles de OpenStreetMap |
| RNF-002 | Rendimiento | Mapa debe cargar en menos de 3s |

## 6. Reglas de negocio

| ID | Regla |
|----|-------|
| RN-001 | prop_id es inmutable - no puede editarse desde el mapa |
| RN-002 | manual_override impide sobrescritura del ETL |
| RN-003 | Coordenadas deben ser válidas (lat -90..90, lng -180..180) |

## 7. Entradas

accion (editar_metadata/editar_hotel/seleccionar_ubicacion), destino_id, prop_id, nombre_visible, latitud, longitud, pais, ciudad, descripcion

## 8. Salidas

Mapa mundial interactivo con marcadores, formularios de edición, confirmación de cambios guardados

## 9. Escenarios

(Gherkin scenarios correspondientes a edición de metadata, edición de nombre hotel, visualización de mapa)

## 10. Criterios de aceptación

| ID | Criterio |
|----|----------|
| CA-001 | Mapa mundial se carga con marcadores de destinos |
| CA-002 | Edición de metadata se guarda correctamente |
| CA-003 | manual_override se activa al editar nombre de hotel |
| CA-004 | Coordenadas inválidas son rechazadas |

## 11. Restricciones

- Requiere internet para tiles del mapa
- manual_override no puede desactivarse una vez activado

## 12. Dependencias

- Leaflet.js (CDN)
- destinations_enriched collection
- dim_hotels collection
- hotel_profile_changes collection

## 13. Fuera de alcance

- Modo offline completo sin internet
- Edición de su descripcion o nombre basandonos que si apunta a ejemplo pais 219, el id es 219 pero nosotros editamos otros campos y mantenemos relacion que todos los 219 docs json pertenecen a ese pais especifco 