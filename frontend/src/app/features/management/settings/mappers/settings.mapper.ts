import type { SettingsDto } from '../models/settings.dto';
import type { SettingsViewModel } from '../models/settings.model';

export function mapSettingsDtoToViewModel(dto: SettingsDto): SettingsViewModel {
  return {
    defaultDashboard: dto.default_dashboard,
    theme: dto.theme,
  };
}
