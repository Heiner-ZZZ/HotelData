import { InjectionToken } from '@angular/core';

export interface ApiConfig {
  baseUrl: string;
  /**
   * Google Maps Embed API key. Exposed in the frontend bundle on purpose —
   * Google restricts it by HTTP referer at the API level, so it's safe to
   * ship. Leave empty to suppress the map iframe on detail pages.
   */
  googleMapsApiKey: string;
}

export const API_CONFIG = new InjectionToken<ApiConfig>('API_CONFIG', {
  providedIn: 'root',
  factory: () => ({
    baseUrl: '/api',
    googleMapsApiKey: '',
  })
});
