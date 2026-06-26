import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import { mapBscResponse } from '../mappers/bsc.mapper';
import type { BscResponseDto } from '../models/bsc.dto';

@Injectable({ providedIn: 'root' })
export class BscApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getBsc() {
    return this.http
      .get<BscResponseDto>(`${this.apiConfig.baseUrl}/kpi/bsc`, {
        withCredentials: true,
      })
      .pipe(catchAuthError(), map(mapBscResponse));
  }
}
