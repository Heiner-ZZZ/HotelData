# Módulo Agrupado: Arquitectura y Experiencia Frontend (Angular)

**Trazabilidad Jerárquica Obligatoria:**
* **Nivel Empresarial**: Operativo (Objetivos OE1, OE2, OE3)
* **Departamento**: Experiencia Cliente, Marketing y Operaciones
* **Paquete UML**: Paquetes de Interfaz de Usuario (Angular Client)
* **Módulos Agrupados**: Autenticación, Gestión Partner, Portal Cliente, Administración, Facturación y Reseñas.

## 1. Objetivo General
Proveer una experiencia de usuario (UX) centralizada, responsiva y orientada a la conversión, basada en un diseño modular de Angular que segrega funcionalidades por roles (RBAC).

## 2. Especificación Técnica Consolidada (Reemplaza specs 043 a 048)
- **Autenticación (Auth)**: Protección de rutas con Guards, inyección de tokens JWT mediante Interceptors y validación de permisos de 9 roles distintos.
- **Módulos Independientes (Lazy Loading)**: El cliente (buscador, reservas, reseñas), el partner (gestión de hotel, inventario, tarifas) y el administrador (geo-catálogo, auditoría) cargan sus módulos bajo demanda para optimizar el First Contentful Paint.
- **Comprobantes y Facturación**: Renderizado visual y exportación (PDF/Impresión) de comprobantes simulados con trazabilidad a la reserva (CU-O24).
