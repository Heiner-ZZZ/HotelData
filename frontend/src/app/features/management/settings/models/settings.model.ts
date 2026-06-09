export interface SettingsViewModel {
  sessionTimeoutMinutes: number;
  defaultDashboard: string;
  theme: string;
}

export interface SelectOption {
  value: string;
  label: string;
}

export const SESSION_TIMEOUT_OPTIONS: SelectOption[] = [
  { value: '15', label: '15 minutos' },
  { value: '30', label: '30 minutos' },
  { value: '60', label: '1 hora' },
  { value: '120', label: '2 horas' },
  { value: '240', label: '4 horas' },
];

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
