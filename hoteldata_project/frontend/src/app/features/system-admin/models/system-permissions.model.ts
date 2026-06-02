export interface SystemPermissionItem {
  permissionCode: string;
  description: string;
}

export interface SystemRolePermissionItem {
  roleName: string;
  description: string;
  permissionCount: number;
  permissionCodesLabel: string;
  accessLabelsLabel: string;
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
