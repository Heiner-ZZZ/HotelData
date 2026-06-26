export interface SettingsViewModel {
  defaultDashboard: string;
  theme: string;
}

export interface SelectOption {
  value: string;
  label: string;
}

export const DASHBOARD_OPTIONS: SelectOption[] = [
  { value: '/management', label: 'Panel hotelero' },
  { value: '/management/reservations', label: 'Reservas' },
  { value: '/management/reports', label: 'Reportes' },
  { value: '/system/monitoring', label: 'Monitoreo' },
];

export const THEME_OPTIONS: SelectOption[] = [
  { value: 'system', label: 'Sistema' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
];
