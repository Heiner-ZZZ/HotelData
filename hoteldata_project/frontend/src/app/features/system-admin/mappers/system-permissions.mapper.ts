import type { SystemPermissionsResponseDto } from '../models/system-permissions.dto';
import type {
  SystemPermissionItem,
  SystemPermissionsViewModel,
  SystemRolePermissionItem
} from '../models/system-permissions.model';

function mapRole(item: SystemPermissionsResponseDto['roles'][number]): SystemRolePermissionItem {
  return {
    roleName: item.role_name,
    description: item.description,
    permissionCount: item.permission_codes.length,
    permissionCodesLabel: item.permission_codes.length ? item.permission_codes.join(', ') : 'Sin permisos',
    accessLabelsLabel: item.access_labels.length ? item.access_labels.join(', ') : 'Sin accesos visibles'
  };
}

function mapPermission(item: SystemPermissionsResponseDto['permissions'][number]): SystemPermissionItem {
  return {
    permissionCode: item.permission_code,
    description: item.description
  };
}

export function mapSystemPermissionsResponse(dto: SystemPermissionsResponseDto): SystemPermissionsViewModel {
  return {
    totals: {
      roles: dto.counts.roles,
      permissions: dto.counts.permissions,
      users: dto.counts.users
    },
    roles: dto.roles.map(mapRole),
    permissions: dto.permissions.map(mapPermission)
  };
}
