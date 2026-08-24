import { SUPERUSER_WILDCARD } from '../../core/auth/permission.constants';

/**
 * Catálogo mínimo de rutas de /management en orden de prioridad para
 * la redirección dinámica. Es un espejo ligero del NAVIGATION_CATALOG
 * canónico (server/scripts/init_security_model_ga03.py) pero solo con
 * los hrefs y su permission_code. El orden importa: el primer href
 * cuyo permiso está satisfecho gana.
 *
 * El primer elemento es el estratégico h01 — los usuarios con
 * reports.strategic.read (gerente, super_admin) deben seguir aterrizando
 * allí, como antes. Para el resto, h01 se salta y se elige el siguiente
 * visible (housekeeping, disponibilidad, etc.).
 *
 * Si ningún /management es visible, se cae a /search (público).
 */
const MANAGEMENT_CANDIDATES: { href: string; permission: string | null }[] = [
  { href: '/management/informes-estrategicos/h01', permission: 'reports.strategic.read' },
  { href: '/management/housekeeping', permission: 'housekeeping.read' },
  { href: '/management/housekeeping/dashboard', permission: 'reports.housekeeping.dashboard.read' },
  { href: '/management/housekeeping/operations', permission: 'reports.housekeeping.operations.read' },
  { href: '/management/housekeeping/matrix', permission: 'reports.housekeeping.matrix.read' },
  { href: '/management/availability', permission: 'inventory.read' },
  { href: '/management/reservations', permission: 'reservations.read' },
  { href: '/management/recepcion', permission: 'reservations.read' },
  { href: '/management/rooms', permission: 'rooms.read' },
  { href: '/management/properties', permission: 'properties.read' },
  { href: '/management/hr/my-portal', permission: 'hr.portal.read' },
  { href: '/management/rates', permission: 'rates.read' },
  { href: '/management/reviews', permission: 'reviews.read' },
  { href: '/management/billing', permission: 'billing.read' },
  { href: '/management/expenses', permission: 'revenue.read' },
];

const ROLE_FALLBACK: Record<string, string> = {
  housekeeping: '/management/housekeeping',
  maintenance: '/management/housekeeping',
  recepcionista: '/management/reservations',
  concierge: '/management/reservations',
  gerente_hotel: '/management/informes-estrategicos/h01',
  hotel_partner: '/management/properties',
  revenue_manager: '/management/rates',
  marketing_hotelero: '/management/amenities',
  super_admin: '/management/informes-estrategicos/h01',
  admin_sistema: '/system/users',
};

/**
 * Elige el primer href bajo /management que el usuario puede abrir,
 * según sus permissionCodes y rol. Es dinámico (no estático) porque
 * depende del conjunto de permisos expandido del backend.
 *
 * - Si tiene *.*, se le concede todo (super_admin) → h01
 * - Si tiene reports.strategic.read → h01
 * - En caso contrario, recorre MANAGEMENT_CANDIDATES en orden y devuelve
 *   el primero donde hasPermission(permiso) es true o permiso es null.
 * - Si ninguno coincide, intenta el fallback por rol (ROLE_DEFAULT_REDIRECTS
 *   espejo) si ese href es accesible.
 * - Último recurso: /search (público)
 */
export function pickFirstAccessibleManagementHref(
  permissionCodes: string[],
  role: string | null | undefined,
): string {
  const has = (code: string | null) => {
    if (!code) return true;
    if (permissionCodes.includes(SUPERUSER_WILDCARD)) return true;
    return permissionCodes.includes(code);
  };

  for (const candidate of MANAGEMENT_CANDIDATES) {
    if (has(candidate.permission)) {
      return candidate.href;
    }
  }

  const fallback = role ? ROLE_FALLBACK[role] : undefined;
  if (fallback && hasRequiredForHref(fallback, permissionCodes)) {
    return fallback;
  }

  return '/search';
}

function hasRequiredForHref(href: string, codes: string[]): boolean {
  const entry = MANAGEMENT_CANDIDATES.find((c) => c.href === href);
  if (!entry) return true;
  if (!entry.permission) return true;
  if (codes.includes(SUPERUSER_WILDCARD)) return true;
  return codes.includes(entry.permission);
}
