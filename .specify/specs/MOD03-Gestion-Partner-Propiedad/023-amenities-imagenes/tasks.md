# Tareas: Amenities e Imágenes

**Input**: [spec.md](spec.md), [plan.md](plan.md)

## Fase 1: Backend

- [ ] T001 Implementar `partner/services/content/save.py`: `update_amenities()`, `update_description()`
- [ ] T002 Implementar `partner/services/content/images.py`: `upload_image()`, `delete_image()`
- [ ] T003 Validar límite de 10 imágenes por propiedad

## Fase 2: Frontend

- [ ] T004 [P] Crear `ContentPage` con editor de descripción larga y highlights
- [ ] T005 [P] Crear `AmenitiesPage` con checkboxes de amenities
- [ ] T006 [P] Galería de imágenes con upload (multipart) y drag & drop para ordenar

## Fase 3: Validación

- [ ] T007 Verificar que primera imagen es la portada
- [ ] T008 Verificar cambios en `hotel_content_changes`
