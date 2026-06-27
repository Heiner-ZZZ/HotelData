# Módulo Agrupado: Infraestructura y Entornos (Docker)

**Trazabilidad Jerárquica Obligatoria:**
* **Nivel Empresarial**: Táctico (Objetivo OE3 - Disponibilidad Técnica)
* **Departamento**: Sistemas y Operaciones IT
* **Paquete UML**: Paquete de Infraestructura y Despliegue
* **Módulos Agrupados**: Dockerización y Variables de Entorno.

## 1. Objetivo General
Garantizar la portabilidad, escalabilidad y aislamiento del sistema mediante contenedores, permitiendo un despliegue transparente tanto en desarrollo como en producción.

## 2. Especificación Técnica Consolidada (Reemplaza specs 049 y 050)
- **Docker Compose**: Orquestación de servicios críticos (FastAPI, MongoDB, Redis, Airflow, Angular) en una misma red virtual aislada (hoteldata-network).
- **Gestión de Configuración**: Inyección centralizada de variables de entorno (.env, settings.py) para evitar la filtración de credenciales y facilitar la mutación entre entornos (Dev, Stage, Prod).
