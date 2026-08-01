export interface SystemPermissionItem {
  permissionCode: string;
  description: string;
}

export interface SystemRolePermissionItem {
  roleName: string;
  description: string;
  permissionCount: number;
  permissionCodes: string[];
  permissionCodesLabel: string;
  accessButtons: { label: string; href: string; icon: string }[];
}

export interface SystemPermissionsViewModel {
  totals: {
    roles: number;
    permissions: number;
    users: number;
  };
  roles: SystemRolePermissionItem[];
  permissions: SystemPermissionItem[];
}

export interface RoleDetailModel {
  role: {
    roleName: string;
    description: string;
    permissionCodes: string[];
    accessButtons: { label: string; href: string; icon: string }[];
    navigationCatalog: { label: string; href: string; icon: string; visible: boolean; permissionId?: string | null }[];
  };
  permissions: SystemPermissionItem[];
}
