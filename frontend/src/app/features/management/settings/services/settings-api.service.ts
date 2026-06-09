import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';
import { HttpClient } from '@angular/common/http';

import { API_CONFIG } from '../../../../core/api/api.config';
import { mapSettingsDtoToViewModel } from '../mappers/settings.mapper';
import type { SettingsDto, SettingsUpdatePayload } from '../models/settings.dto';

export interface PasswordChangeResponse {
  ok: boolean;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class SettingsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getSettings() {
    return this.http
      .get<SettingsDto>(`${this.apiConfig.baseUrl}/settings`, { withCredentials: true })
      .pipe(map(dto => mapSettingsDtoToViewModel(dto)));
  }

  updateSettings(payload: SettingsUpdatePayload) {
    return this.http
      .put<SettingsDto>(`${this.apiConfig.baseUrl}/settings`, payload, { withCredentials: true })
      .pipe(map(dto => mapSettingsDtoToViewModel(dto)));
  }

  changePassword(currentPassword: string, newPassword: string) {
    return this.http.put<PasswordChangeResponse>(
      `${this.apiConfig.baseUrl}/settings/password`,
      { current_password: currentPassword, new_password: newPassword },
      { withCredentials: true },
    );
  }
}
