/**
 * Permission-section grouping for the role editor ("Permisos — Matriz CRUD").
 *
 * The flat 90-code CRUD matrix is grouped by the SAME sections the sidebar
 * uses (Sistema, Gestión·Dashboard/PMS, Gestión·Reservas/CRS, Housekeeping,
 * RRHH, Revenue, Billing, Cliente) so an admin sees — at a glance and without
 * reading English — which menu each permission controls.
 *
 * All functions here are pure so the grouping and the LIVE per-section nav
 * preview (computed client-side, no server round-trip) are unit-testable.
 *
 * KEEP IN SYNC: the section keys mirror `server/src/app/security/navigation.py`
 * (``section`` field of the ``navigation`` collection) and the sidebar groups.
 */

export type SectionKey =
  | 'Sistema'
  | 'PMS'
  | 'CRS'
  | 'Housekeeping'
  | 'RRHH'
  | 'Revenue'
  | 'Billing'
  | 'Cliente';

export interface SectionDef {
  key: SectionKey;
  /** Título legible del grupo (el de "sub-menú" del sidebar). */
  title: string;
  icon: string;
}

export const SECTION_DEFS: readonly SectionDef[] = [
  { key: 'Sistema', title: 'Sistema', icon: 'admin_panel_settings' },
  { key: 'PMS', title: 'Gestión · Dashboard', icon: 'dashboard' },
  { key: 'CRS', title: 'Gestión · Reservas', icon: 'book_online' },
  { key: 'Housekeeping', title: 'Gestión · Housekeeping', icon: 'cleaning_services' },
  { key: 'RRHH', title: 'Gestión · RRHH', icon: 'badge' },
  { key: 'Revenue', title: 'Gestión · Revenue', icon: 'trending_up' },
  { key: 'Billing', title: 'Gestión · Facturación', icon: 'receipt' },
  { key: 'Cliente', title: 'Cliente', icon: 'person' },
];

const MANAGE_CRUD_ACTIONS = ['create', 'read', 'update', 'delete'] as const;

/** Acciones base SIEMPRE dibujadas en la matriz CRUD, en este orden. */
export const MATRIX_BASE_ACTIONS = ['manage', 'read', 'create', 'update', 'delete'] as const;

/** Acciones CONDICIONALES: su columna solo se dibuja si al menos un recurso
 *  del catálogo la tiene (ej. ``execute``, ``moderate``). Si ningún permiso de
 *  la matriz ofrece la opción, la columna desaparece en vez de quedar vacía. */
export const MATRIX_CONDITIONAL_ACTIONS = ['execute', 'moderate'] as const;

/** Recurso del CRUD con sus acciones (para contar/filtrar secciones). */
export interface ResourceActionsRow {
  resource: string;
  actions: Record<string, { code: string; description?: string } | undefined>;
}

/** Permiso del catálogo que la matriz CRUD NO puede dibujar como checkbox. */
export interface HiddenPermissionItem {
  code: string;
  description?: string;
}

/** ¿La matriz CRUD puede dibujar este código como checkbox? Requiere recurso NO
 *  vacío y acción conocida (espejo EXACTO del filtro de ``resourceRows`` de la
 *  página: ``if (!resource || !KNOWN_ACTIONS.has(action)) continue``). */
export function isMatrixVisibleCode(code: string, knownActions: readonly string[]): boolean {
  const [resource, action] = code.split('.', 2);
  return Boolean(resource) && knownActions.includes(action);
}

/** Códigos del catálogo que la matriz CRUD no renderiza — el complemento exacto
 *  de ``isMatrixVisibleCode``: ej. ``properties.approve``, ``hotel.manage_roles``
 *  o ``inventory.products.cost.read`` (y códigos con recurso vacío). Son permisos
 *  reales: la página los muestra como chips en su sección para que el conteo
 *  global cuadre (visible + hidden == total del catálogo, 87 + 4 = 91). */
export function matrixHiddenCodes(
  permissions: readonly { code: string; description?: string }[],
  knownActions: readonly string[],
): HiddenPermissionItem[] {
  return permissions.filter((permission) => !isMatrixVisibleCode(permission.code, knownActions));
}

/** Conteo combinado de una sección: matriz CRUD + códigos compuestos/ocultos.
 *  La suma de secciones con este conteo cuadra con el total global del catálogo
 *  (visible + hidden, sin doble conteo: los ocultos nunca están en ``resources``). */
export function countSectionCodesWithHidden(
  resources: ResourceActionsRow[],
  hiddenCodes: readonly { code: string }[],
  selectedCodes: readonly string[],
): { selected: number; total: number } {
  const matrix = countSectionCodes(resources, selectedCodes);
  const selectedSet = new Set(selectedCodes);
  const hiddenSelected = hiddenCodes.filter((permission) => selectedSet.has(permission.code)).length;
  return { selected: matrix.selected + hiddenSelected, total: matrix.total + hiddenCodes.length };
}

/** Conteo ``{ selected, total }`` de códigos de una sección: total = suma de
 *  acciones del catálogo; selected = cuántas están en la selección. Se usa en
 *  la cabecera de cada sección de la matriz ("PMS · 12/19"). */
export function countSectionCodes(
  resources: ResourceActionsRow[],
  selectedCodes: readonly string[],
): { selected: number; total: number } {
  const selected = new Set(selectedCodes);
  let total = 0;
  let selectedCount = 0;
  for (const row of resources) {
    for (const permission of Object.values(row.actions)) {
      if (!permission) continue;
      total++;
      if (selected.has(permission.code)) selectedCount++;
    }
  }
  return { selected: selectedCount, total };
}

/** Filtra recursos por nombre, código completo o descripción (insensible a
 *  mayúsculas). Vacío/espacios → devuelve todo. Usado por el buscador de la
 *  matriz para localizar recursos sin salir de la página. */
export function filterResourcesByQuery(
  resources: ResourceActionsRow[],
  query: string,
): ResourceActionsRow[] {
  const q = query.trim().toLowerCase();
  if (!q) return resources;
  return resources.filter((row) => {
    if (row.resource.toLowerCase().includes(q)) return true;
    return Object.values(row.actions).some((permission) => {
      if (!permission) return false;
      return (
        permission.code.toLowerCase().includes(q) ||
        (permission.description ?? '').toLowerCase().includes(q)
      );
    });
  });
}

/** Columnas de la matriz CRUD: siempre las acciones base (``MATRIX_BASE_ACTIONS``)
 *  en su orden, más las acciones condicionales (``MATRIX_CONDITIONAL_ACTIONS`` —
 *  ``execute``/``moderate``) SOLO si al menos un recurso del catálogo las tiene.
 *  Así ``etl.execute``/``reviews.moderate`` son toggleables desde la UI sin
 *  mostrar columnas vacías en catálogos que no las usan. */
export function matrixActionColumns<const T extends readonly string[]>(
  resources: ResourceActionsRow[],
  baseActions: T,
  extraActions: readonly string[],
): string[] {
  const present = new Set<string>();
  for (const row of resources) {
    for (const action of Object.keys(row.actions)) {
      if (!(baseActions as readonly string[]).includes(action) && extraActions.includes(action)) {
        present.add(action);
      }
    }
  }
  return [...baseActions, ...extraActions.filter((action) => present.has(action))];
}

/** Expande ``resource.manage`` → CRUD (espejo de ``expand_permissions`` del
 *  server). Los códigos compuestos (``hotel.manage_roles``) no se expanden. */
export function expandManageCodes(codes: string[]): Set<string> {
  const expanded = new Set<string>(codes);
  for (const code of codes) {
    if (!code.includes('.')) continue;
    const [resource, action] = code.split('.', 2);
    if (action === 'manage') {
      for (const a of MANAGE_CRUD_ACTIONS) expanded.add(`${resource}.${a}`);
    }
  }
  return expanded;
}

/** Recurso (primer segmento del código) → sección primaria. */
const RESOURCE_SECTIONS: Record<string, SectionKey> = {
  // Sistema
  users: 'Sistema',
  roles: 'Sistema',
  audit: 'Sistema',
  monitoring: 'Sistema',
  etl: 'Sistema',
  settings: 'Sistema',
  // Gestión · Dashboard (PMS)
  dashboard: 'PMS',
  properties: 'PMS',
  hotels: 'PMS',
  rooms: 'PMS',
  amenities: 'PMS',
  promotions: 'PMS',
  shifts: 'PMS',
  hotel: 'PMS',
  reviews: 'PMS',
  // Gestión · Reservas (CRS)
  reservations: 'CRS',
  inventory: 'CRS',
  rates: 'CRS',
  'check-ins': 'CRS',
  'check-outs': 'CRS',
  // Housekeeping
  housekeeping: 'Housekeeping',
  maintenance: 'Housekeeping',
  charges: 'Housekeeping',
  'lost-found': 'Housekeeping',
  // RRHH
  hr: 'RRHH',
  // Revenue
  revenue: 'Revenue',
  reports: 'Revenue',
  // Billing
  billing: 'Billing',
  payments: 'Billing',
  // Cliente
  account: 'Cliente',
  search: 'Cliente',
};

/** Sección de un recurso (primer segmento) para la fila de la tabla CRUD.
 *  Códigos legacy ``crud.*`` caen a Sistema vía fallback; ``hotel`` (Equipo y
 *  permisos) se mapea a Gestión·Dashboard. */
export function sectionForResource(resource: string): SectionKey {
  return RESOURCE_SECTIONS[resource] ?? 'Sistema';
}

const KNOWN_NAV_SECTIONS: readonly SectionKey[] = ['PMS', 'CRS', 'Housekeeping', 'RRHH', 'Revenue', 'Billing'];

/** Sección de un ítem del catálogo de navegación (para la vista previa). */
export function sectionForNavItem(item: { href?: string | null; section?: string | null }): SectionKey {
  if (item.section && (KNOWN_NAV_SECTIONS as readonly string[]).includes(item.section)) {
    return item.section as SectionKey;
  }
  const href = item.href ?? '';
  if (href.startsWith('/system') || href.startsWith('/admin') || href.startsWith('/ownership')) {
    return 'Sistema';
  }
  if (href.startsWith('/search') || href.startsWith('/account')) {
    return 'Cliente';
  }
  return 'PMS';
}

/**
 * Visibilidad en vivo de un ítem de navegación: visible si su permiso
 * requerido está seleccionado (o lo cubre un ``manage``/wildcard). Replica la
 * regla del server ``get_all_navigation_items`` sin round-trip HTTP.
 */
export function isNavItemVisible(
  item: { requiredPermission?: string | null },
  selectedCodes: string[],
): boolean {
  if (!item.requiredPermission) return true;
  const expanded = expandManageCodes(selectedCodes);
  if (expanded.has('*.*')) return true;
  return expanded.has(item.requiredPermission);
}
