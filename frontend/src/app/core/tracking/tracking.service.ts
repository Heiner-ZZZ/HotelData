import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../api/api.config';

@Injectable({ providedIn: 'root' })
export class TrackingService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /** Log a click on a hotel from search results or detail page. */
  trackHotelClick(propId: number, source: 'search' | 'detail' | 'compare' = 'search'): void {
    this.http.post(
      `${this.apiConfig.baseUrl}/tracking/hotel-click`,
      { prop_id: propId, source },
      { withCredentials: true }
    ).subscribe({
      error: () => { /* silent fail — tracking must never block UX */ }
    });
  }
}
