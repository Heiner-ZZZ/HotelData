/**
 * Helpers puros del panel de auditoría por rol.
 *
 * Separados del componente para poder testear la lógica de diff sin TestBed
 * (mismo patrón que hotel-search/mappers).
 */
import type { HotelRole, RoleAuditEntry, RoleTemplate } from './hotel-permissions.model';

export interface PermissionDiff {
  added: string[];
  removed: string[];
}

/**
 * Diff de permisos de una entrada del historial. Devuelve null cuando la
 * entrada no tocó permisos (solo renombrado / estado).
 */
export function permissionDiff(entry: RoleAuditEntry): PermissionDiff | null {
  const p = entry.diff?.['permissions'];
  if (!p || !Array.isArray(p.old) || !Array.isArray(p.new)) return null;
  const oldSet = new Set(p.old as string[]);
  const newSet = new Set(p.new as string[]);
  return {
    added: (p.new as string[]).filter((c) => !oldSet.has(c)),
    removed: (p.old as string[]).filter((c) => !newSet.has(c)),
  };
}

/**
 * Diff del rol actual vs su plantilla base. Se usa como fallback cuando el
 * rol se creó antes de que existiera el historial (entries vacías).
 */
export function templatePermissionDiff(
  role: HotelRole,
  templates: RoleTemplate[],
): PermissionDiff | null {
  const tpl = templates.find((t) => t.id === role.basedOnRoleId);
  if (!tpl) return null;
  const oldSet = new Set(tpl.permissions);
  const newSet = new Set(role.permissions);
  return {
    added: role.permissions.filter((c) => !oldSet.has(c)),
    removed: tpl.permissions.filter((c) => !newSet.has(c)),
  };
}
