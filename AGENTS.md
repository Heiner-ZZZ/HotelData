<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# Reglas para Codebuff (Buffy)

## 🔴 NUNCA hacer sin autorización explícita del usuario

- **🚫 ABSOLUTAMENTE NUNCA** ejecutar `docker compose down` sin `--volumes` ni ningún comando que elimine volúmenes de Docker.
- **🚫 NUNCA** ejecutar `docker compose down` para reconstruir contenedores — usar `up --build` en su lugar.
- **🚫 NUNCA** ejecutar `docker compose down -v`.
- **NUNCA** hacer `git commit`, `git push` ni ningún comando de git que modifique el historial sin autorización.
- **NUNCA** eliminar archivos, directorios, colecciones de MongoDB, tablas o datos sin preguntar.
- **NUNCA** ejecutar scripts que modifiquen la base de datos en producción (seed, drop, reset) sin confirmación.
- **NUNCA** sobrescribir archivos de configuración (`.env`, `docker-compose.yml`, etc.) sin informar.

## ✅ Docker — Estándar para desarrollo

Basado en [Docker docs: build best practices](https://docs.docker.com/build/building/best-practices/):

| Situación | Comando | Por qué |
|-----------|---------|---------|
| Solo cambió código fuente (TS, HTML, Python) | `docker compose up -d <servicio>` | Sin rebuild — el código se monta por volumen en dev. Para producción sí rebuild. |
| Cambió `Dockerfile`, `package.json`, `requirements.txt` o similar | `docker compose up -d --build <servicio>` | Rebuild inteligente — Docker reusa capas inalteradas (ej: `npm install` solo si cambió `package.json`). |
| Cache corrompido, error extraño de build, o dependencias stale | `docker compose build --no-cache <servicio>` | Solo cuando sea necesario — rebuild completo de todas las capas (lento). |

**Reglas:**
- Usar `docker compose -f infra/docker-compose.yml up --build <servicio>` para rebuild + logs visibles en primer plano.
- **NO** usar `--no-cache` en rebuilds rutinarios — desperdicia tiempo redescargando dependencias inalteradas.
- Si el servicio monta volúmenes de código (dev), no hace falta rebuild para cambios de código fuente.
- Preferir `docker compose up -d` (detached) cuando no se necesiten logs en terminal.
- **NUNCA** usar datos hardcodeados (`standard`, `deluxe`, `suite`, etc.) en seed scripts o queries — siempre leer dinámicamente de la BD.

## ⚙️ ETL (Incremental)

El pipeline GA03 soporta dos modos controlados por la env var `GA03_INCREMENTAL_MODE` (default: `"false"`):

### Modo Full (default, `GA03_INCREMENTAL_MODE=false`)
- Extrae TODOS los registros de PocketBase
- `delete_many({})` + inserciones en MongoDB (borra y reescribe todo)
- El comportamiento histórico no cambia

### Modo Incremental (`GA03_INCREMENTAL_MODE=true`)
- **1er run**: Extrae todo, guarda `last_extracted_at` (max `created` de PocketBase) en `ga03_execution_state.json`
- **Runs siguientes**: El extract filtra por `(created>last_extracted_at)`, solo extrae registros nuevos
- Las dimensiones se cargan con `UpdateOne` + `upsert=True` (no borra lo existente)
- Los hechos se cargan con `UpdateOne` por `source_record_id` + `upsert=True` (no borra nada, solo agrega nuevos)
- `expected_records` en estado = cantidad de registros **nuevos** extraídos (no el total)
- Si se pierde el archivo de estado, el próximo run será full automáticamente

### Elección
- Para recargar todo desde 0: `GA03_INCREMENTAL_MODE=false` (o no setearla)
- Para agregar solo nuevos: `GA03_INCREMENTAL_MODE=true`
