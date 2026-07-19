import { HttpClient, HttpEvent } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

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

  getProfile() {
    return this.http
      .get<ProfileDto>('/account/profile')
      .pipe(map((dto) => mapProfileDtoToViewModel(dto)));
  }

  updateProfile(payload: ProfileUpdatePayload) {
    return this.http
      .put<ProfileDto>('/account/profile', payload)
      .pipe(map((dto) => mapProfileDtoToViewModel(dto)));
  }

  getSessions() {
    return this.http.get<{ items: unknown[]; total: number }>('/auth/sessions');
  }

  terminateOtherSessions() {
    return this.http.post<{ ok: boolean; message: string; terminated_count: number }>(
      '/auth/sessions/terminate-others',
      {},
    );
  }

  changePassword(currentPassword: string, newPassword: string): Observable<{ ok: boolean; message: string }> {
    return this.http.put<{ ok: boolean; message: string }>('/api/settings/password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  uploadAvatar(file: File): Observable<HttpEvent<AvatarUploadResponse>> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<AvatarUploadResponse>('/account/profile/avatar', formData, {
      reportProgress: true,
      observe: 'events',
    });
  }
}
