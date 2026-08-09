export interface SystemUsersResponseDto {
  counts: {
    users: number;
    roles: number;
  };
  current_user: {
    username: string;
    primary_role_id?: string;
    primary_role: string;
  };
  users: {
    user_id: string;
    username: string;
    email: string;
    display_name: string;
    primary_role: string;
    primary_role_id?: string;
    role_names: string[];
    is_active: boolean;
    created_at: string | null;
    assigned_hotels: {
      prop_id: number;
      label: string;
    }[];
    is_current_user: boolean;
    is_protected: boolean;
    can_toggle: boolean;
    toggle_label: string;
    action_hint: string;
  }[];
  roles: {
    role_name: string;
    description: string;
  }[];
}

export interface SystemUserRoleDto {
  role_name: string;
  description: string;
}

export interface SystemUserUpdatePayloadDto {
  username?: string;
  display_name?: string;
  email?: string;
  primary_role?: string;
  is_active?: boolean;
  password?: string;
  assigned_hotels?: number[];
}

export interface HotelSearchResultDto {
  prop_id: number;
  label: string;
  display_country_label?: string | null;
}

export interface SystemUserUpdateResponseDto {
  ok: boolean;
  message: string;
}

export interface SystemUserToggleResponseDto {
  ok: boolean;
  message: string;
}
