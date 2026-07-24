import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapMyNotifications } from '../mappers/notifications.mapper';
import type { MyNotificationsDto } from '../models/notifications.dto';

@Injectable({ providedIn: 'root' })
export class ClientNotificationsService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getMyNotifications(page = 1, pageSize = 10) {
    const params = new HttpParams()
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<MyNotificationsDto>(`${this.apiConfig.baseUrl}/notifications/my`, { params, withCredentials: true })
      .pipe(map(dto => mapMyNotifications(dto)));
  }
}
