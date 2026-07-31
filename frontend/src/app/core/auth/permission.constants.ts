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
  | (string & {});
