/**
 * Centralized map of role machine names to human-readable Spanish labels.
 *
 * Used by nav components, profile pages, and anywhere a role is displayed.
 * The role name (key) comes from the backend's ``get_role_name()`` which
 * resolves it from ``primary_role_id`` (ObjectId FK → roles._id).
 */
export const ROLE_LABELS: Record<string, string> = {
  super_admin: 'Super Administrador',
  admin_sistema: 'Admin. Sistema',
  hotel_partner: 'Hotel Partner',
  gerente_hotel: 'Gerente de Hotel',
  revenue_manager: 'Revenue Manager',
  marketing_hotelero: 'Marketing Hotelero',
  auditor_datos: 'Auditor de Datos',
  operador_datos: 'Operador de Datos',
  maintenance: 'Mantenimiento',
  recepcionista: 'Recepcionista',
  housekeeping: 'Housekeeping',
  concierge: 'Concierge',
  cliente: 'Cliente',
};

/**
 * Resolve a human-readable label from a role machine name.
 * Returns the label if known, otherwise the name with underscores
 * replaced by spaces and title-cased.
 */
export function roleLabel(roleName: string | undefined | null): string {
  if (!roleName) return 'Usuario';
  return ROLE_LABELS[roleName] || roleName.replace(/_/g, ' ');
}
