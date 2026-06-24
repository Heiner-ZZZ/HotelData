import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapNotificationsList } from '../mappers/notifications.mapper';
import type { NotificationsListDto } from '../models/notifications.dto';
import type { NotificationsViewModel } from '../models/notifications.model';

@Injectable({ providedIn: 'root' })
export class NotificationsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getNotifications(page = 1, notificationType?: string, startDate?: string, endDate?: string) {
    let params = new HttpParams().set('page', String(page));
    if (notificationType) {
      params = params.set('notification_type', notificationType);
    }
    if (startDate) {
      params = params.set('start_date', startDate);
    }
    if (endDate) {
      params = params.set('end_date', endDate);
    }
    return this.http
      .get<NotificationsListDto>(`${this.apiConfig.baseUrl}/admin/notifications`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapNotificationsList(dto)));
  }
}
