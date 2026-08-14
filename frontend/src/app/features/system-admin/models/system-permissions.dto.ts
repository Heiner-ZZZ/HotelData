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

export interface NavigationItemDto {
  slug: string;
  parentSlug: string | null;
  position: number;
  nodeType: string | null;
  label: string;
  href: string;
  icon: string;
  visible: boolean;
  permissionId?: string | null;
  permissionCode?: string | null;
}

export interface RoleDetailResponseDto {
  role: {
    _id: string;
    role_name: string;
    description: string;
    permission_codes: string[];
    access_buttons: { label: string; href: string; icon: string }[];
    navigation_catalog: NavigationItemDto[];
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

export interface NavigationPreviewItemDto extends NavigationItemDto {}

export interface NavigationPreviewResponseDto {
  navigation_catalog: NavigationPreviewItemDto[];
}
