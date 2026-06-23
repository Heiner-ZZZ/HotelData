# Plan de Implementación: Amenities e Imágenes

**Branch**: `023-amenities-imagenes` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Frontend                            Backend                          MongoDB
─────────────────                   ─────────────────                ──────
                                                     ┌──────────────────────────┐
  /management/content ─────────────►               │ partner/services/        │
  (amenities, imágenes,              CRUD            │ content/save.py          │──► hotel_content_pages
   descripciones)                    /api/partner/   │ content/images.py        │──► hotel_images
                                      content/       │ (update_amenities,       │
                                                     │  upload_image,           │
                                                     │  update_description)     │
                                                     └──────────────────────────┘
```

## Endpoints

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | /api/partner/properties/{id}/content | Obtener contenido completo |
| PUT | /api/partner/properties/{id}/content/amenities | Actualizar amenities |
| POST | /api/partner/properties/{id}/content/images | Subir imagen (multipart) |
| DELETE | /api/partner/properties/{id}/content/images/{img_id} | Eliminar imagen |
| PUT | /api/partner/properties/{id}/content/description | Actualizar descripción larga y highlights |

## Reglas de negocio

- Las imágenes se almacenan como base64 o URL (según implementación)
- Máximo 10 imágenes por propiedad
- La primera imagen es la principal (portada)
- Amenities son un array de strings (checkboxes en UI)
- Los cambios se registran en `hotel_content_changes`
