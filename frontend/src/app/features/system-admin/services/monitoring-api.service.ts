import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';
import type { ActionResponseDto } from '../models/monitoring.dto';


interface UploadResult {
  ok: boolean;
  uploaded_filename: string;
  display_message: string;
}

@Injectable({ providedIn: 'root' })
export class MonitoringApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  triggerValidate(target = 0) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/validate?target=${target}`,
      {},
      { withCredentials: true },
    );
  }

  triggerRunPipeline(target = 0, incremental = false) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/run?target=${target}&incremental=${incremental}`,
      {},
      { withCredentials: true },
    );
  }

  triggerSeed(target = 0, incremental = false) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/seed?target=${target}&incremental=${incremental}`,
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

  triggerStop(process: string) {
    return this.http.post<ActionResponseDto>(
      `${this.apiConfig.baseUrl}/etl-status/ga03/stop?process=${process}`,
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
