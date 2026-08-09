export interface SystemUserRoleOption {
  roleName: string;
  description: string;
}

export interface AssignedHotel {
  propId: number;
  label: string;
}

export interface SystemUserListItem {
  userId: string;
  username: string;
  email: string;
  displayName: string;
  primaryRole: string;
  primaryRoleId: string;
  roleNamesLabel: string;
  isActive: boolean;
  createdAtLabel: string;
  assignedHotels: AssignedHotel[];
  isCurrentUser: boolean;
  isProtected: boolean;
  canEdit: boolean;
  canToggle: boolean;
  toggleLabel: string;
  actionHint: string;
}

export interface SystemUsersViewModel {
  totalUsers: number;
  totalRoles: number;
  currentUsername: string;
  items: SystemUserListItem[];
  roles: SystemUserRoleOption[];
}
