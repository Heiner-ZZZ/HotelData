/**
 * Permission code constants — single source of truth for permission
 * identifiers used by AuthService.hasPermission, the roleGuard, and any
 * domain-specific feature code that needs to gate a UI element.
 *
 * The auth system accepts any string permission code, but these constants
 * document the well-known codes that appear in the codebase. Use them
 * instead of string literals so a typo or rename gets caught at compile
 * time AND ``api/api-context`` semantics stay in sync between Pydantic
 * (server) and TypeScript (frontend).
 *
 * The ``PermissionCode`` type accepts the known codes literally for IDE
 * autocompletion AND any string (via ``(string & {})``) for forward
 * compatibility with server-added codes that haven't been mirrored here
 * yet — this keeps the door open for backend-first migrations without a
 * frontend rename.
 */

/** Wildcard granted to ``super_admin`` and ``admin_sistema``. Grants every permission check. */
export const SUPERUSER_WILDCARD = '*.*';

// ── Shift management (server: server/src/app/modules/reception/routes.py) ──
/** Gerencia turnos: bypass de schedule-check, force-open conflictado. */
export const SHIFTS_MANAGE = 'shifts.manage';
/** Abrir turno nuevo dentro del schedule normal. */
export const SHIFTS_CREATE = 'shifts.create';
/** Cerrar turno + realizar depósito / arqueo de caja. */
export const SHIFTS_UPDATE = 'shifts.update';

// ── Lost & Found (server: server/src/app/modules/lost_and_found/routes.py) ──
/** Administrar objetos perdidos — acceso total. */
export const LOST_FOUND_MANAGE = 'lost-found.manage';
/** Registrar objeto perdido/encontrado. */
export const LOST_FOUND_CREATE = 'lost-found.create';
/** Ver registros de lost & found (gate del nav item y del listado). */
export const LOST_FOUND_READ = 'lost-found.read';
/** Editar / reclamar / desechar registros. */
export const LOST_FOUND_UPDATE = 'lost-found.update';
/** Eliminar registros de lost & found. */
export const LOST_FOUND_DELETE = 'lost-found.delete';

// ── Equipo y permisos del hotel (server: server/src/app/modules/hotel_permissions/) ──
/** Gestionar roles y permisos del equipo en un hotel (gate del nav item). */
export const HOTEL_MANAGE_ROLES = 'hotel.manage_roles';

// ── Informes (server: server/src/app/modules/reports/routes.py + reports.* codes) ──
/** Descargar/exportar informes (CSV/XLSX/PDF) — global a lo que ya puedes leer. */
export const REPORTS_DOWNLOAD = 'reports.download';

// ── RRHH granular por interfaz (server: server/src/app/modules/hr/routes.py) ──
/** Mi Portal — auto-servicio del empleado. */
export const HR_PORTAL_READ = 'hr.portal.read';
/** Directorio: ver empleados, departamentos, documentos. */
export const HR_DIRECTORY_READ = 'hr.directory.read';
/** Directorio: crear/editar/eliminar empleados, departamentos, documentos. */
export const HR_DIRECTORY_MANAGE = 'hr.directory.manage';
/** Onboarding: crear empleados + transferir permisos. */
export const HR_ONBOARDING_CREATE = 'hr.onboarding.create';
/** Turnos: ver horarios. */
export const HR_SHIFTS_READ = 'hr.shifts.read';
/** Turnos: crear/editar/eliminar y registrar check-in/check-out. */
export const HR_SHIFTS_MANAGE = 'hr.shifts.manage';

/**
 * Permission-code marker. Use everywhere a permission check happens:
 *
 *   this.auth.hasPermission(SHIFTS_CREATE)
 *   this.auth.hasPermission(SUPERUSER_WILDCARD)
 *   this.auth.hasPermission('shifts.create' as PermissionCode) // string literal still works
 */
export type PermissionCode =
  | typeof SUPERUSER_WILDCARD
  | typeof SHIFTS_MANAGE
  | typeof SHIFTS_CREATE
  | typeof SHIFTS_UPDATE
  | typeof LOST_FOUND_MANAGE
  | typeof LOST_FOUND_CREATE
  | typeof LOST_FOUND_READ
  | typeof LOST_FOUND_UPDATE
  | typeof LOST_FOUND_DELETE
  | typeof HOTEL_MANAGE_ROLES
  | typeof REPORTS_DOWNLOAD
  | typeof HR_PORTAL_READ
  | typeof HR_DIRECTORY_READ
  | typeof HR_DIRECTORY_MANAGE
  | typeof HR_ONBOARDING_CREATE
  | typeof HR_SHIFTS_READ
  | typeof HR_SHIFTS_MANAGE
  | (string & {});
