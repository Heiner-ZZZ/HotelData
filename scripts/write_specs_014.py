#!/usr/bin/env python3
"""Write detailed spec content to all 37 spec files (014-050)."""
import os
import sys

BASE = os.path.join(os.path.dirname(__file__), '..', '.specify', 'specs')

# Each spec: folder_name -> content
specs = {}

specs['014-editar-nombre-comercial'] = """# Especificación: Editar Nombre Comercial

**Versión**: 1.0 | **Estado**: Draft | **Última actualización**: 2026-06-22

**Casos de uso TAF06**: CU-O12 (Actualizar perfil de propiedad), CU-T03 (Validar y auditar cambios en datos de propiedad)

## 1. Objetivo

Permitir que el hotel partner edite el nombre comercial de su propiedad con manual_override, preservando el prop_id técnico y registrando todos los cambios en el historial de auditoría.

## 2. Contexto

Las propiedades hoteleras tienen un prop_id técnico (asignado por el sistema o el ETL) que no debe modificarse. El nombre comercial es un campo de presentación que el partner puede personalizar. Los cambios se guardan en manual_override para no pisar datos provenientes del ETL. Cada cambio queda registrado en hotel_profile_changes para trazabilidad.

## 3. Actores

| Actor | Descripción |
|-------|-------------|
| Hotel partner | Edita nombre comercial de sus propiedades asignadas |
| Gerente de hotel | Edita nombre comercial de las propiedades que gestiona |
| Super Admin | Edita nombre comercial de cualquier propiedad |

## 4. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | El sistema debe permitir editar el nombre comercial de la propiedad | Alta |
| RF-002 | El sistema debe preservar el prop_id técnico sin modificaciones | Alta |
| RF-003 | El sistema debe guardar el cambio en manual_override.nombre_comercial | Alta |
| RF-004 | El sistema debe registrar cada cambio en hotel_profile_changes con old/new value | Alta |
| RF-005 | El sistema debe actualizar verified_at al modificar el nombre | Media |
| RF-006 | El sistema debe validar que el hotel pertenece al partner que edita | Alta |

## 5. Requisitos no funcionales

| ID | Requisito |
|----|-----------|
| RNF-001 | La operación debe completarse en menos de 500ms |
| RNF-002 | Solo campos en whitelist pueden ser modificados (protección contra mass assignment) |
| RNF-003 | El historial de cambios debe conservarse indefinidamente |

## 6. Reglas de negocio

- prop_id no se puede modificar bajo ninguna circunstancia
- El nombre comercial se almacena en manual_override para no sobrescribir datos ETL
- Cada cambio se registra en hotel_profile_changes con hotel_id, field, old_value, new_value, changed_by, changed_at
- Solo hotel_partner, gerente_hotel y super_admin pueden editar
- El hotel debe estar asignado al partner (verificación de propiedad)
- verified_at se actualiza a now() cuando cambia el nombre

## 7. Entradas

```json
{
  "nombre_comercial": "Hotel Vista Hermosa Premium"
}
```

## 8. Salidas

```json
{
  "success": true,
  "data": {
    "prop_id": "HOTEL001",
    "nombre_comercial": "Hotel Vista Hermosa Premium",
    "manual_override": {
      "nombre_comercial": "Hotel Vista Hermosa Premium",
      "updated_by": "user_abc123",
      "updated_at": "2026-06-22T10:30:00Z"
    },
    "verified_at": "2026-06-22T10:30:00Z"
  }
}
```

## 9. Escenarios

### Escenario 1: Edicion exitosa de nombre comercial
```gherkin
Dado que el hotel partner esta autenticado
Y tiene asignada la propiedad HOTEL001
Cuando envia PUT /api/partner/properties/HOTEL001/profile
Y el body contiene el nuevo nombre comercial
Entonces el sistema responde 200
Y el campo nombre_comercial se actualiza en hotels.manual_override
Y se registra el cambio en hotel_profile_changes
```

### Escenario 2: Partner intenta editar propiedad no asignada
```gherkin
Dado que el hotel partner esta autenticado
Y NO tiene asignada la propiedad HOTEL999
Cuando envia PUT /api/partner/properties/HOTEL999/profile
Entonces el sistema responde 403 Forbidden
```

## 10. Criterios de aceptacion

| ID | Criterio |
|----|----------|
| CA-001 | El nombre comercial se actualiza correctamente |
| CA-002 | prop_id permanece sin cambios despues de la edicion |
| CA-003 | El cambio queda registrado en hotel_profile_changes |
| CA-004 | verified_at se actualiza al modificar el nombre |
| CA-005 | Partner sin asignacion recibe 403 |

## 11. Restricciones

- El nombre comercial no puede estar vacio
- Longitud maxima: 200 caracteres
- No se permiten caracteres especiales no imprimibles

## 12. Dependencias

- Coleccion hotels (lectura/escritura)
- Coleccion hotel_profile_changes (insert)
- Modulo partner/services/profile.py
- Middleware de autenticacion y verificacion de propiedad

## 13. Fuera de alcance

- Edicion de otros campos del perfil (cubierto en otros specs)
- Sincronizacion con PocketBase o fuente ETL
"""

# Write all spec files
written = 0
errors = 0
for folder, content in specs.items():
    filepath = os.path.join(BASE, folder, 'spec.md')
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        written += 1
        print(f'OK: {folder}')
    except Exception as e:
        errors += 1
        print(f'ERROR: {folder}: {e}')

print(f'\nTotal: {written} written, {errors} errors')
sys.exit(0 if errors == 0 else 1)
