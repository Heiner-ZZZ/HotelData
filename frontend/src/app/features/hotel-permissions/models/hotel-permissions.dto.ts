/**
 * DTOs for the Fase 2 UI "Equipo y permisos del hotel".
 *
 * KEEP IN SYNC: espejo de los `*Response` de
 * `server/src/app/modules/hotel_permissions/routes.py`:
 *   - HotelRoleResponse / HotelRoleListResponse
 *   - RoleTemplateResponse
 *   - AssignmentResponse / HotelTeamResponse / TeamMemberResponse
 *   - ActionResponse
 *   - RoleAuditResponse / RoleAuditEntryResponse (GET /roles/{id}/audit)
 */

export interface HotelRoleDto {
  id: string;
  prop_id: number;
  name: string;
  display_name: string;
  permissions: string[];
  based_on_role_id: string | null;
  based_on: string;
  is_active: boolean;
  is_system: boolean;
  assignment_count: number;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface RoleAuditEntryDto {
  timestamp: string | null;
  action: string;
  changed_by: string;
  summary: string;
  diff: Record<string, { old: unknown; new: unknown }> | null;
}

export interface RoleAuditDto {
  id: string;
  name: string;
  display_name: string;
  based_on: string;
  created_by: string;
  created_at: string | null;
  updated_at: string | null;
  permission_count: number;
  entries: RoleAuditEntryDto[];
}

export interface RoleTemplateDto {
  id: string;
  role_name: string;
  display_name: string;
  permissions: string[];
}

export interface HotelRoleListDto {
  items: HotelRoleDto[];
  templates: RoleTemplateDto[];
  permission_codes: string[];
}

export interface TeamMemberDto {
  user_id: string;
  username: string;
  display_name: string;
}

export interface AssignmentDto {
  id: string;
  prop_id: number;
  user_id: string;
  username: string;
  display_name: string;
  role_id: string;
  role_name: string;
  role_display_name: string;
  assigned_by: string;
  assigned_at: string | null;
}

export interface HotelTeamDto {
  assigned: AssignmentDto[];
  unassigned_staff: TeamMemberDto[];
}

export interface ActionResponseDto {
  ok: boolean;
  message: string;
}

// ── Payloads ──

export interface CreateRolePayload {
  name: string;
  display_name?: string;
  permissions: string[];
  based_on_role_id?: string | null;
}

export interface UpdateRolePayload {
  display_name?: string;
  permissions?: string[];
  is_active?: boolean;
}

export interface AssignRolePayload {
  user_id: string;
  role_id: string;
}

export interface ChangeRolePayload {
  role_id: string;
}
