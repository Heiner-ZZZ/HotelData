# Especificacion: ETL - Ingesta de Datos

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-T12 (Ejecutar y validar pipeline Airflow)

## 1. Objetivo

Extraer datos desde PocketBase y CSV, validar esquema, y convertir a JSONL + Parquet.

## 2. Contexto

El pipeline ingiere datos desde PocketBase y los transforma a formato intermedio antes de cargar a MongoDB.

## 3. Requisitos funcionales

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-001 | Extraer datos desde PocketBase via API | Alta |
| RF-002 | Extraer datos desde CSV local | Alta |
| RF-003 | Validar esquema minimo de columnas requeridas | Alta |
| RF-004 | Convertir a JSONL (staging) | Alta |
| RF-005 | Convertir a Parquet (processed) | Alta |
| RF-006 | Procesar en chunks de 50k filas | Alta |

## 4. Flujo de datos

PocketBase - JSONL - Parquet - Dimensiones (upsert) - Fact (batch insert) - MongoDB

## 5. Dependencias

- server/src/etl/tasks.py
- server/src/etl/transform_clean.py
- PocketBase como fuente de datos
