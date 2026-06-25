import { HttpClient, HttpEvent } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapProfileDtoToViewModel } from '../mappers/profile.mapper';
import type { ProfileDto, ProfileUpdatePayload } from '../models/profile.dto';

export interface AvatarUploadResponse {
  ok: boolean;
  avatar_url: string;
  message: string;
}

@Injectable({
  providedIn: 'root',
})
export class ProfileApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getProfile() {
    return this.http
      .get<ProfileDto>(`${this.apiConfig.baseUrl}/account/profile`, {
        withCredentials: true,
      })
      .pipe(map((dto) => mapProfileDtoToViewModel(dto)));
  }

  updateProfile(payload: ProfileUpdatePayload) {
    return this.http
      .put<ProfileDto>(`${this.apiConfig.baseUrl}/account/profile`, payload, {
        withCredentials: true,
      })
      .pipe(map((dto) => mapProfileDtoToViewModel(dto)));
  }

  getSessions() {
    return this.http.get<{ items: unknown[]; total: number }>(
      `${this.apiConfig.baseUrl}/auth/sessions`,
      { withCredentials: true },
    );
  }

  terminateOtherSessions() {
    return this.http.post<{ ok: boolean; message: string; terminated_count: number }>(
      `${this.apiConfig.baseUrl}/auth/sessions/terminate-others`,
      {},
      { withCredentials: true },
    );
  }

  uploadAvatar(file: File): Observable<HttpEvent<AvatarUploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<AvatarUploadResponse>(
      `${this.apiConfig.baseUrl}/account/profile/avatar`,
      formData,
      {
        withCredentials: true,
        reportProgress: true,
        observe: 'events',
      },
    );
  }
}
