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
    is_current_user: boolean;
    is_protected: boolean;
    can_toggle: boolean;
    toggle_label: string;
    action_hint: string;
  }[];
}

export interface SystemUserToggleResponseDto {
  ok: boolean;
  message: string;
}
