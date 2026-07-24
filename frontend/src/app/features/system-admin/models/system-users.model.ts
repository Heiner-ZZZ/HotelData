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
  canToggle: boolean;
  toggleLabel: string;
  actionHint: string;
}

export interface SystemUsersViewModel {
  totalUsers: number;
  totalRoles: number;
  currentUsername: string;
  items: SystemUserListItem[];
}
