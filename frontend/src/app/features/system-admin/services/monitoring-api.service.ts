import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { forkJoin, map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapMonitoringData } from '../mappers/monitoring.mapper';
import type {
  ActionResponseDto,
  ExecutionStatusResponseDto,
  Ga03ProgressResponseDto,
  ReportsResponseDto,
  ServicesResponseDto,
} from '../models/monitoring.dto';
import type { MonitoringViewModel } from '../models/monitoring.model';


interface UploadResult {
  ok: boolean;
  uploaded_filename: string;
  display_message: string;
}

@Injectable({ providedIn: 'root' })
export class MonitoringApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getMonitoringData() {
    return forkJoin({
      services: this.http.get<ServicesResponseDto>(`${this.apiConfig.baseUrl}/etl-status/services`, { withCredentials: true }),
      reports: this.http.get<ReportsResponseDto>(`${this.apiConfig.baseUrl}/etl-status/reports`, { withCredentials: true }),
      progress: this.http.get<Ga03ProgressResponseDto>(`${this.apiConfig.baseUrl}/etl-status/ga03/progress`, { withCredentials: true }),
      execution: this.http.get<ExecutionStatusResponseDto>(`${this.apiConfig.baseUrl}/etl-status/execution`, { withCredentials: true }),
    }).pipe(
      map(({ services, reports, progress, execution }) =>
        mapMonitoringData(services, reports, progress, execution),
      ),
    );
  }

  triggerValidate(target = 0) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/validate?target=${target}`,
      {},
      { withCredentials: true },
    );
  }

  triggerRunPipeline(target = 0) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/run?target=${target}`,
      {},
      { withCredentials: true },
    );
  }

  triggerSeed(target = 0) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/seed?target=${target}`,
      {},
      { withCredentials: true },
    );
  }

  triggerClearEvidence() {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/clear-evidence`,
      {},
      { withCredentials: true },
    );
  }

  uploadCsv(file: File) {
    const formData = new FormData();
    formData.append('ga03_source_file', file);
    return this.http.post<UploadResult>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/upload-csv`,
      formData,
      { withCredentials: true },
    );
  }
}
