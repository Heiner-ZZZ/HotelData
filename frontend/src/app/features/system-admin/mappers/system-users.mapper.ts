import type { SystemUserToggleResponseDto, SystemUsersResponseDto } from '../models/system-users.dto';
import type { SystemUserListItem, SystemUsersViewModel } from '../models/system-users.model';

function formatDate(value: string | null): string {
  if (!value) {
    return 'N/D';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat('es-EC', {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(date);
}

function mapUser(item: SystemUsersResponseDto['users'][number]): SystemUserListItem {
  const isCurrentUser = item.is_current_user;
  const isProtected = item.is_protected;
  return {
    userId: item.user_id,
    username: item.username,
    email: item.email,
    displayName: item.display_name,
    primaryRole: item.primary_role,
    primaryRoleId: item.primary_role_id || '',
    roleNamesLabel: item.role_names.length ? item.role_names.join(', ') : 'Sin roles',
    isActive: item.is_active,
    createdAtLabel: formatDate(item.created_at),
    assignedHotels: (item.assigned_hotels || []).map((h) => ({ propId: h.prop_id, label: h.label })),
    isCurrentUser,
    isProtected,
    canEdit: !isCurrentUser && !isProtected,
    canToggle: item.can_toggle,
    toggleLabel: item.toggle_label,
    actionHint: item.action_hint || ''
  };
}

export function mapSystemUsersResponse(dto: SystemUsersResponseDto): SystemUsersViewModel {
  return {
    totalUsers: dto.counts.users,
    totalRoles: dto.counts.roles,
    currentUsername: dto.current_user.username,
    items: dto.users.map(mapUser),
    roles: (dto.roles || []).map((role) => ({
      roleName: role.role_name,
      description: role.description
    }))
  };
}

export function mapSystemUserToggleResult(dto: SystemUserToggleResponseDto) {
  return {
    ok: dto.ok,
    message: dto.message
  };
}
