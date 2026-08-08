import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  ActionResponseDto,
  AssignRolePayload,
  AssignmentDto,
  ChangeRolePayload,
  CreateRolePayload,
  HotelRoleDto,
  HotelRoleListDto,
  HotelTeamDto,
  RoleAuditDto,
  TeamMemberDto,
  UpdateRolePayload,
} from '../models/hotel-permissions.dto';
import type { HotelRole, RoleAssignment, RoleAudit, RoleTemplate, TeamMember } from '../models/hotel-permissions.model';

export function mapHotelRole(dto: HotelRoleDto): HotelRole {
  return {
    id: dto.id,
    propId: dto.prop_id,
    name: dto.name,
    displayName: dto.display_name,
    permissions: dto.permissions ?? [],
    basedOnRoleId: dto.based_on_role_id ?? null,
    basedOn: dto.based_on ?? '',
    isActive: dto.is_active ?? true,
    isSystem: dto.is_system ?? false,
    assignmentCount: dto.assignment_count ?? 0,
    createdBy: dto.created_by ?? '',
    createdAt: dto.created_at ?? null,
    updatedAt: dto.updated_at ?? null,
  };
}

export function mapRoleAudit(dto: RoleAuditDto): RoleAudit {
  return {
    id: dto.id,
    name: dto.name,
    displayName: dto.display_name,
    basedOn: dto.based_on,
    createdBy: dto.created_by ?? '',
    createdAt: dto.created_at ?? null,
    updatedAt: dto.updated_at ?? null,
    permissionCount: dto.permission_count ?? 0,
    entries: (dto.entries ?? []).map((e) => ({
      timestamp: e.timestamp ?? null,
      action: e.action,
      changedBy: e.changed_by ?? '',
      summary: e.summary ?? '',
      diff: e.diff ?? null,
    })),
  };
}

export function mapTemplate(dto: { id: string; role_name: string; display_name: string; permissions: string[] }): RoleTemplate {
  return {
    id: dto.id,
    roleName: dto.role_name,
    displayName: dto.display_name || dto.role_name,
    permissions: dto.permissions ?? [],
  };
}

export function mapMember(dto: TeamMemberDto): TeamMember {
  return {
    userId: dto.user_id,
    username: dto.username,
    displayName: dto.display_name || dto.username,
  };
}

export function mapAssignment(dto: AssignmentDto): RoleAssignment {
  return {
    id: dto.id,
    propId: dto.prop_id,
    userId: dto.user_id,
    username: dto.username,
    displayName: dto.display_name || dto.username,
    roleId: dto.role_id,
    roleName: dto.role_name,
    roleDisplayName: dto.role_display_name || dto.role_name,
    assignedBy: dto.assigned_by,
    assignedAt: dto.assigned_at ?? null,
  };
}

@Injectable({ providedIn: 'root' })
export class HotelPermissionsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/management/hotels`;

  // ── hotel_roles ──

  listRoles(propId: number): Observable<HotelRoleListDto> {
    return this.http.get<HotelRoleListDto>(`${this.base}/${propId}/roles`, { withCredentials: true });
  }

  createRole(propId: number, payload: CreateRolePayload): Observable<HotelRole> {
    return this.http
      .post<HotelRoleDto>(`${this.base}/${propId}/roles`, payload, { withCredentials: true })
      .pipe(map(mapHotelRole));
  }

  updateRole(propId: number, roleId: string, payload: UpdateRolePayload): Observable<HotelRole> {
    return this.http
      .put<HotelRoleDto>(`${this.base}/${propId}/roles/${roleId}`, payload, { withCredentials: true })
      .pipe(map(mapHotelRole));
  }

  deleteRole(propId: number, roleId: string): Observable<ActionResponseDto> {
    return this.http.delete<ActionResponseDto>(`${this.base}/${propId}/roles/${roleId}`, { withCredentials: true });
  }

  // ── role_assignments ──

  listAssignments(propId: number): Observable<HotelTeamDto> {
    return this.http.get<HotelTeamDto>(`${this.base}/${propId}/assignments`, { withCredentials: true });
  }

  assignUser(propId: number, payload: AssignRolePayload): Observable<RoleAssignment> {
    return this.http
      .post<AssignmentDto>(`${this.base}/${propId}/assignments`, payload, { withCredentials: true })
      .pipe(map(mapAssignment));
  }

  changeAssignmentRole(propId: number, assignmentId: string, payload: ChangeRolePayload): Observable<RoleAssignment> {
    return this.http
      .put<AssignmentDto>(`${this.base}/${propId}/assignments/${assignmentId}`, payload, { withCredentials: true })
      .pipe(map(mapAssignment));
  }

  unassignUser(propId: number, assignmentId: string): Observable<ActionResponseDto> {
    return this.http.delete<ActionResponseDto>(`${this.base}/${propId}/assignments/${assignmentId}`, { withCredentials: true });
  }
}
