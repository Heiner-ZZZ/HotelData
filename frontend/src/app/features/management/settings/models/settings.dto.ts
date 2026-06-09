export interface SettingsDto {
  session_timeout_minutes: number;
  default_dashboard: string;
  theme: string;
}

export interface SettingsUpdatePayload {
  session_timeout_minutes?: number;
  default_dashboard?: string;
  theme?: string;
}
