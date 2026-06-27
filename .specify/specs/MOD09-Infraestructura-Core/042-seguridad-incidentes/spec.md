# Especificacion: Seguridad e Incidentes

**Version**: 1.0 | **Estado**: Draft | **Ultima actualizacion**: 2026-06-22

**Casos de uso TAF06**: CU-O01, CU-T09 (Arquitectura de seguridad, perimetro, activos, plan de incidentes)

## 1. Objetivo

Definir la arquitectura de seguridad del sistema: perimetro, activos protegidos, plan de incidentes educacional.

## 2. Contexto

Proyecto educacional sin datos reales de huespedes. La postura de seguridad previene exposicion accidental.

## 3. Perimetro de seguridad

Internet (solo frontend Angular) - Nginx (proxy, TLS) - FastAPI (auth, RBAC) - MongoDB (red interna Docker)

## 4. Activos protegidos

| Activo | Proteccion |
|--------|-----------|
| Credenciales | bcrypt + sesiones TTL 8h |
| Sesiones | Hash SHA-256 en DB, cookie httponly |
| .env | .gitignore + env_file Docker |

## 5. Fuera de alcance (seguridad enterprise)

Rate limiting, CSRF tokens, PCI DSS, cifrado en reposo, hardening de contenedores
