# Especificación: Tipos de Habitación y Gestión de Inventario

**Versión**: 1.1 | **Estado**: Actualizado | **Última actualización**: 2026-06-21

**Casos de uso TA07**: CU-O14 (Crear tipo de habitación), CU-O30 (Gestionar disponibilidad y estado de habitaciones)

## 1. Objetivo
Crear y gestionar tipos de habitación, habitaciones físicas, y la consulta de estado/disponibilidad de cada habitación.

## 2. Contexto
Este spec fue expandido para incluir la gestión de estado y disponibilidad de habitaciones individuales (anteriormente CU-O30), ahora fusionada con la creación de tipos de habitación.

## 3. Actores
| Actor | Descripción |
|-------|-------------|
| Hotel partner | Crea y configura tipos de habitación |
| Recepcionista | Consulta estado y disponibilidad |

## 4. Requisitos funcionales
| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Crear tipo de habitación con nombre, capacidad, cantidad | Alta |
| RF-002 | Crear N habitaciones físicas al crear el tipo | Alta |
| RF-003 | Consultar estado de todas las habitaciones del hotel | Alta |
| RF-004 | Cambiar estado de habitación individual | Alta |
| RF-005 | Ver calendario de disponibilidad por habitación | Alta |
