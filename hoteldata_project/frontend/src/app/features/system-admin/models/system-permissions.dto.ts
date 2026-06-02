export interface SystemPermissionsResponseDto {
  counts: {
    users: number;
    roles: number;
    permissions: number;
    sessions: number;
    activity: number;
  };
  roles: Array<{
    role_name: string;
    description: string;
    permission_codes: string[];
    access_labels: string[];
  }>;
  permissions: Array<{
    permission_code: string;
    description: string;
  }>;
}
