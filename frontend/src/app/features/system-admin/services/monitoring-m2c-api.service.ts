import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  M2cActionResponseDto,
  M2cConsolidatedDto,
  M2cScheduleDto,
  M2cScheduleUpdateDto,
} from '../models/monitoring-m2c.dto';

@Injectable({ providedIn: 'root' })
export class MonitoringM2cApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getConsolidated() {
    return this.http.get<M2cConsolidatedDto>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/consolidated`,
      { withCredentials: true },
    );
  }

  getProgress() {
    return this.http.get<M2cConsolidatedDto['progress']>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/progress`,
      { withCredentials: true },
    );
  }

  triggerRun() {
    return this.http.post<M2cActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/run`,
      {},
      { withCredentials: true },
    );
  }

  triggerStop() {
    return this.http.post<M2cActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/stop`,
      {},
      { withCredentials: true },
    );
  }

  getSchedule() {
    return this.http.get<M2cScheduleDto>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/schedule`,
      { withCredentials: true },
    );
  }

  updateSchedule(payload: M2cScheduleUpdateDto) {
    return this.http.put<M2cActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/m2c/schedule`,
      payload,
      { withCredentials: true },
    );
  }
}
