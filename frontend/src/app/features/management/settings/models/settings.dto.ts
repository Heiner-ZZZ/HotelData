export interface SettingsDto {
  default_dashboard: string;
  theme: string;
}

export interface SettingsUpdatePayload {
  default_dashboard?: string;
  theme?: string;
}
