# Plan de Implementación: Seguridad e Incidentes

**Branch**: `042-seguridad-incidentes` | **Spec**: [spec.md](spec.md)

## Arquitectura

```
Internet (solo frontend Angular)
  → Nginx (proxy, TLS)
    → FastAPI (auth session cookie, RBAC)
      → MongoDB (red interna Docker)
```

## Activos protegidos

| Activo | Protección |
|--------|-----------|
| Credenciales | bcrypt + sesiones TTL 8h |
| Sesiones | Hash SHA-256 en DB, cookie httponly |
| .env | .gitignore + env_file Docker |

## Entregables

Este spec es principalmente documentación de la arquitectura de seguridad existente:

1. Diagrama de perímetro de seguridad
2. Tabla de activos protegidos
3. Plan de incidentes educacional
4. Estrategia de backup & recovery
5. Lo que está fuera de alcance (seguridad enterprise)

## Fuera de alcance (documentado)

Rate limiting, CSRF tokens, PCI DSS, cifrado en reposo, hardening de contenedores
