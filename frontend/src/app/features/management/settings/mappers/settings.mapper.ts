import type { SettingsDto } from '../models/settings.dto';
import type { SettingsViewModel } from '../models/settings.model';

export function mapSettingsDtoToViewModel(dto: SettingsDto): SettingsViewModel {
  return {
    sessionTimeoutMinutes: dto.session_timeout_minutes,
    defaultDashboard: dto.default_dashboard,
    theme: dto.theme,
  };
}
