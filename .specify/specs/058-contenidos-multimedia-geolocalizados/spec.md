# Especificación: Gestionar Contenidos Multimedia con Geolocalización

**Versión**: 1.0 | **Estado**: Draft | **CU TA07**: CU-O37

## 1. Objetivo
Gestionar contenidos multimedia (fotos, videos, tours virtuales) asociados a coordenadas geográficas específicas, enriqueciendo la presentación de hoteles y destinos.

## 2. Actores
| Actor | Descripción |
|-------|-------------|
| Marketing hotelero | Sube, geolocaliza y actualiza contenido |

## 3. Requisitos funcionales
| ID | Requisito |
|----|-----------|
| RF-001 | Subir fotos (JPEG/PNG/WebP, máx 20MB) y videos (MP4/WebM, máx 50MB) |
| RF-002 | Geolocalizar contenido arrastrando marcador en mapa |
| RF-003 | Almacenar en MongoDB GridFS |
| RF-004 | Marcar contenido como principal o inactivo |

## 4. Reglas de negocio
- Coordenadas opcionales para contenido general, obligatorias para ubicaciones específicas
- Máximo 100 archivos multimedia por hotel

## 5. Colecciones
hotel_multimedia, fs.files + fs.chunks (GridFS)