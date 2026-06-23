<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->

# Reglas para Codebuff (Buffy)

## 🔴 NUNCA hacer sin autorización explícita del usuario

- **NUNCA** ejecutar `docker compose down -v` ni ningún comando que elimine volúmenes de Docker.
- **NUNCA** ejecutar `docker compose down` sin preguntar primero.
- **NUNCA** hacer `git commit`, `git push` ni ningún comando de git que modifique el historial sin autorización.
- **NUNCA** eliminar archivos, directorios, colecciones de MongoDB, tablas o datos sin preguntar.
- **NUNCA** ejecutar scripts que modifiquen la base de datos en producción (seed, drop, reset) sin confirmación.
- **NUNCA** sobrescribir archivos de configuración (`.env`, `docker-compose.yml`, etc.) sin informar.

## ✅ Siempre hacer

- Preguntar antes de cualquier operación que pueda destruir datos.
- Confirmar con el usuario antes de reiniciar servicios que puedan afectar la disponibilidad.
- Informar claramente qué va a hacer antes de ejecutar comandos potencialmente destructivos.
