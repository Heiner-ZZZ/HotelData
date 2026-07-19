import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../api/api.config';
import { AuthService } from '../auth/auth.service';

@Injectable({ providedIn: 'root' })
export class TrackingService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly authService = inject(AuthService);

  /** Log a click on a hotel from search results or detail page.
   *  Silently skips if the user is not authenticated (avoids 401 noise). */
  trackHotelClick(propId: number, source: 'search' | 'detail' | 'compare' = 'search'): void {
    if (!this.authService.isAuthenticated()) return;
    this.http.post(
      `${this.apiConfig.baseUrl}/tracking/hotel-click`,
      { prop_id: propId, source },
      { withCredentials: true }
    ).subscribe({
      error: () => { /* silent fail — tracking must never block UX */ }
    });
  }
}
