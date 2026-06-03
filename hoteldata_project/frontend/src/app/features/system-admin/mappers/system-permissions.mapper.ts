import type { RoleDetailResponseDto, SystemPermissionsResponseDto } from '../models/system-permissions.dto';
import type {
  RoleDetailModel,
  SystemPermissionItem,
  SystemPermissionsViewModel,
  SystemRolePermissionItem
} from '../models/system-permissions.model';

const ICON_MAP: Record<string, string> = {
  'icon-admin': 'admin_panel_settings',
  'icon-auth': 'vpn_key',
  'icon-dashboard': 'dashboard',
  'icon-analytics': 'analytics',
  'icon-records': 'receipt_long',
  'icon-revenue': 'payments',
  'icon-booking': 'calendar_month',
  'icon-partner': 'business',
  'icon-hotels': 'hotel',
  'icon-etl': 'sync_alt',
};

function mapAccessButton(b: { label: string; href: string; icon: string }): { label: string; href: string; icon: string } {
  return { label: b.label, href: b.href, icon: ICON_MAP[b.icon] || b.icon || 'arrow_right' };
}

function mapNavigationItem(b: { label: string; href: string; icon: string; visible: boolean }): { label: string; href: string; icon: string; visible: boolean } {
  return { label: b.label, href: b.href, icon: ICON_MAP[b.icon] || b.icon || 'arrow_right', visible: b.visible };
}

function mapRole(item: SystemPermissionsResponseDto['roles'][number]): SystemRolePermissionItem {
  return {
    roleName: item.role_name,
    description: item.description,
    permissionCount: item.permission_codes.length,
    permissionCodesLabel: item.permission_codes.length ? item.permission_codes.join(', ') : 'Sin permisos',
    accessButtons: (item.access_buttons || []).map(mapAccessButton)
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

export function mapRoleDetailResponse(dto: RoleDetailResponseDto): RoleDetailModel {
  return {
    role: {
      roleName: dto.role.role_name,
      description: dto.role.description,
      permissionCodes: dto.role.permission_codes,
      accessButtons: (dto.role.access_buttons || []).map(mapAccessButton),
      navigationCatalog: (dto.role.navigation_catalog || []).map(mapNavigationItem),
    },
    permissions: (dto.permissions || []).map(p => ({
      permissionCode: p.permission_code,
      description: p.description
    }))
  };
}
