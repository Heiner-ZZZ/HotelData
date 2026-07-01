<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# Reglas para Codebuff (Buffy)

## 🔴 NUNCA hacer sin autorización explícita del usuario

- **🚫 ABSOLUTAMENTE NUNCA** ejecutar `docker compose down` bajo NINGUNA circunstancia, ni aunque el usuario lo pida explícitamente. Para reconstruir contenedores usar SOLO `docker compose up -d --build`. o `docker compose -f infra/docker-compose.yml build --no-cache frontend`
`docker compose -f infra/docker-compose.yml up -d` o la del server
- **🚫 ABSOLUTAMENTE NUNCA** ejecutar `docker compose down -v` ni ningún comando que elimine volúmenes de Docker.
- **NUNCA** hacer `git commit`, `git push` ni ningún comando de git que modifique el historial sin autorización.
- **NUNCA** eliminar archivos, directorios, colecciones de MongoDB, tablas o datos sin preguntar.
- **NUNCA** ejecutar scripts que modifiquen la base de datos en producción (seed, drop, reset) sin confirmación.
- **NUNCA** sobrescribir archivos de configuración (`.env`, `docker-compose.yml`, etc.) sin informar.

## ✅ Siempre hacer

- Preguntar antes de cualquier operación que pueda destruir datos.
- Confirmar con el usuario antes de reiniciar servicios que puedan afectar la disponibilidad.
- Informar claramente qué va a hacer antes de ejecutar comandos potencialmente destructivos.
- Para reconstruir contenedores usar SIEMPRE `docker compose up -d --build <servicio>` (NUNCA `docker compose down`).
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
