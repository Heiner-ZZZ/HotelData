export interface SystemPermissionsResponseDto {
  counts: {
    users: number;
    roles: number;
    permissions: number;
    sessions: number;
    activity: number;
  };
  roles: {
    role_name: string;
    description: string;
    permission_codes: string[];
    access_buttons: { label: string; href: string; icon: string }[];
  }[];
  permissions: {
    permission_code: string;
    description: string;
  }[];
}

export interface RoleDetailResponseDto {
  role: {
    _id: string;
    role_name: string;
    description: string;
    permission_codes: string[];
    access_buttons: { label: string; href: string; icon: string }[];
    navigation_catalog: { label: string; href: string; icon: string; visible: boolean }[];
    created_at?: string;
    updated_at?: string;
  };
  permissions: {
    permission_code: string;
    description: string;
  }[];
}

export interface RoleUpdateRequestDto {
  description: string;
  permission_codes: string[];
}
