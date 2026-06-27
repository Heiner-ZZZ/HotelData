# Especificacion: Amenities e Imagenes

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O21 (Actualizar amenities, imagenes y contenido comercial), CU-T08 (Validar contenido multimedia de propiedades)

## 1. Objetivo

Actualizar amenities, imagenes y contenido comercial de la propiedad para mejorar la presentacion en el portal de busqueda y detalle del hotel.

## 2. Contexto

El contenido comercial del hotel incluye amenities (piscina, wifi, gym, etc.), imagenes (fotos de la propiedad) y descripciones. Este contenido se muestra al cliente en la busqueda y detalle del hotel.

## 3. Actores

| Actor | Descripcion |
|-------|-------------|
| Marketing hotelero | Actualiza amenities, imagenes y contenido comercial |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir actualizar lista de amenities | Alta |
| RF-002 | El sistema debe permitir subir imagenes (multipart) | Alta |
| RF-003 | El sistema debe permitir eliminar imagenes | Alta |
| RF-004 | El sistema debe permitir reordenar imagenes (la primera es portada) | Alta |
| RF-005 | El sistema debe permitir editar descripcion larga y highlights | Alta |
| RF-006 | El sistema debe limitar a 10 imagenes por propiedad | Alta |
| RF-007 | El sistema debe registrar cambios en hotel_content_changes | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | Subida de imagen menos de 2s (imagen menos de 5MB) |
| RNF-002 | El contenido debe servirse rapido con cache CDN |

## 6. Reglas de negocio

- Las imagenes se almacenan como base64 o URL (segun implementacion)
- Maximo 10 imagenes por propiedad
- La primera imagen es la principal (portada)
- Amenities son un array de strings (checkboxes en UI)
- Los cambios se registran en hotel_content_changes

## 7. Entradas

```json
{
  "amenities": ["wifi", "piscina", "gimnasio", "restaurante", "estacionamiento", "spa"],
  "description": "Hermoso hotel frente al mar con todas las comodidades...",
  "highlights": ["Vista al mar", "Desayuno incluido", "Piscina climatizada"]
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "hotel_id": "HOTEL001",
    "amenities": ["wifi", "piscina", "gimnasio", "restaurante", "estacionamiento", "spa"],
    "images_count": 5,
    "primary_image": "https://.../img_001.jpg",
    "updated_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Actualizar amenities
```gherkin
Dado que el partner edita el contenido del hotel
Cuando selecciona amenities y escribe descripcion
Entonces el sistema guarda en hotel_content_pages
Y registra el cambio en hotel_content_changes
```

### Escenario 2: Subir imagen
```gherkin
Dado que el partner sube una imagen (multipart)
Cuando la imagen es valida (menos de 5MB)
Entonces el sistema la guarda en hotel_images
Y la muestra en la galeria
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | Amenities se actualizan correctamente |
| CA-002 | Imagenes se suben y eliminan correctamente |
| CA-003 | Limite de 10 imagenes se respeta |
| CA-004 | Descripcion se guarda correctamente |
| CA-005 | Cambios quedan en hotel_content_changes |

## 11. Restricciones

- Imagen maxima 5MB, formatos: JPEG, PNG, WebP
- Descripcion maxima 5000 caracteres
- Maximo 10 imagenes, 50 amenities

## 12. Dependencias

- Coleccion hotel_content_pages
- Coleccion hotel_images
- Coleccion hotel_content_changes
- Modulo partner/services/content/save.py y content/images.py

## 13. Fuera de alcance

- Procesamiento automatico de imagenes (thumbnails, optimizacion)
- Videos de propiedad
