/**
 * Domain models + permission-catalog grouping helpers for the Fase 2 UI
 * "Equipo y permisos del hotel".
 */

export interface HotelRole {
  id: string;
  propId: number;
  name: string;
  displayName: string;
  permissions: string[];
  basedOnRoleId: string | null;
  basedOn: string;
  isActive: boolean;
  isSystem: boolean;
  assignmentCount: number;
  /** Usuario que creó el rol (documentado en hotel_roles.created_by). */
  createdBy: string;
  createdAt: string | null;
  updatedAt: string | null;
}

/** Un campo del diff de auditoría (ej. permissions, display_name, is_active). */
export interface RoleAuditDiffField {
  old: unknown;
  new: unknown;
}

/** Una entrada del historial de auditoría de un rol (fila de audit_log). */
export interface RoleAuditEntry {
  timestamp: string | null;
  action: 'create' | 'update' | 'delete' | string;
  changedBy: string;
  summary: string;
  diff: Record<string, RoleAuditDiffField> | null;
}

/** Resumen + historial devueltos por GET /roles/{id}/audit. */
export interface RoleAudit {
  id: string;
  name: string;
  displayName: string;
  basedOn: string;
  createdBy: string;
  createdAt: string | null;
  updatedAt: string | null;
  permissionCount: number;
  entries: RoleAuditEntry[];
}

export interface RoleTemplate {
  id: string;
  roleName: string;
  displayName: string;
  permissions: string[];
}

export interface TeamMember {
  userId: string;
  username: string;
  displayName: string;
}

export interface RoleAssignment {
  id: string;
  propId: number;
  userId: string;
  username: string;
  displayName: string;
  roleId: string;
  roleName: string;
  roleDisplayName: string;
  assignedBy: string;
  assignedAt: string | null;
}

export interface PermissionItem {
  code: string;
  label: string;
}

export interface PermissionGroup {
  resource: string;
  label: string;
  icon: string;
  permissions: PermissionItem[];
}

// ── Catalog labels ────────────────────────────────────────────────────

/** resource → módulo legible + icono Material Symbols para agrupar checkboxes. */
const MODULE_META: Record<string, { label: string; icon: string }> = {
  hotel: { label: 'Administración del hotel', icon: 'admin_panel_settings' },
  dashboard: { label: 'Dashboard', icon: 'dashboard' },
  reservations: { label: 'Reservas', icon: 'book_online' },
  'check-ins': { label: 'Check-ins', icon: 'login' },
  'check-outs': { label: 'Check-outs', icon: 'logout' },
  properties: { label: 'Propiedades', icon: 'apartment' },
  hotels: { label: 'Hoteles', icon: 'hotel' },
  rooms: { label: 'Habitaciones', icon: 'bed' },
  rates: { label: 'Tarifas', icon: 'sell' },
  revenue: { label: 'Revenue', icon: 'trending_up' },
  reports: { label: 'Reportes', icon: 'description' },
  housekeeping: { label: 'Housekeeping', icon: 'cleaning_services' },
  maintenance: { label: 'Mantenimiento', icon: 'build' },
  charges: { label: 'Cargos', icon: 'attach_money' },
  inventory: { label: 'Inventario', icon: 'inventory_2' },
  hr: { label: 'RRHH', icon: 'badge' },
  billing: { label: 'Facturación', icon: 'receipt' },
  payments: { label: 'Pagos', icon: 'payments' },
  shifts: { label: 'Turnos y cajas', icon: 'point_of_sale' },
  amenities: { label: 'Amenities', icon: 'spa' },
  promotions: { label: 'Promociones', icon: 'campaign' },
  settings: { label: 'Configuración', icon: 'settings' },
  audit: { label: 'Auditoría', icon: 'receipt_long' },
  monitoring: { label: 'Monitoreo', icon: 'monitoring' },
  etl: { label: 'ETL / Datos', icon: 'storage' },
  users: { label: 'Usuarios', icon: 'people' },
  roles: { label: 'Roles', icon: 'admin_panel_settings' },
  account: { label: 'Cuenta', icon: 'account_circle' },
  search: { label: 'Búsqueda', icon: 'search' },
};

const ACTION_LABELS: Record<string, string> = {
  create: 'Crear',
  read: 'Ver',
  update: 'Editar',
  delete: 'Eliminar',
  manage: 'Gestionar',
  execute: 'Ejecutar',
  // Acciones compuestas del catálogo (Fase 2)
  manage_roles: 'Roles y permisos del equipo',
};

function moduleMeta(resource: string): { label: string; icon: string } {
  return MODULE_META[resource] ?? { label: resource, icon: 'more_horiz' };
}

function actionLabel(action: string): string {
  const known = ACTION_LABELS[action];
  if (known) return known;
  // Acciones compuestas del catálogo (ej. inventory.products.cost.read):
  // usar la etiqueta del último segmento (read → "Ver"). El código completo
  // se muestra como hint en la UI.
  if (action.includes('.')) {
    const last = action.split('.').pop() ?? '';
    const knownLast = ACTION_LABELS[last];
    if (knownLast) return knownLast;
  }
  // Fallback genérico: "manage_roles" → "Manage Roles" → "Manage roles"
  const readable = action
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
  return readable || 'Acceso';
}

/** Divide "resource.action" → (resource, action). El código completo se
 *  muestra como hint; "hotel.manage_roles" es una excepción del formato. */
function splitCode(code: string): { resource: string; action: string } {
  if (code === 'hotel.manage_roles') return { resource: 'hotel', action: 'manage_roles' };
  const idx = code.indexOf('.');
  if (idx <= 0) return { resource: code, action: '' };
  return { resource: code.slice(0, idx), action: code.slice(idx + 1) };
}

/** Agrupa los códigos del catálogo por módulo, ordenados para los checkboxes. */
export function groupPermissions(codes: string[]): PermissionGroup[] {
  const grouped = new Map<string, PermissionItem[]>();
  for (const code of codes) {
    const { resource, action } = splitCode(code);
    if (!grouped.has(resource)) grouped.set(resource, []);
    grouped.get(resource)!.push({
      code,
      label: actionLabel(action),
    });
  }
  return [...grouped.entries()]
    .map(([resource, permissions]) => {
      const meta = moduleMeta(resource);
      permissions.sort((a, b) => a.label.localeCompare(b.label, 'es'));
      return { resource, label: meta.label, icon: meta.icon, permissions };
    })
    .sort((a, b) => a.label.localeCompare(b.label, 'es'));
}

/** Etiqueta corta para mostrar el permiso en chips (ej. "Ver" para reservations.read). */
export function shortPermissionLabel(code: string): string {
  const { action } = splitCode(code);
  return actionLabel(action);
}
