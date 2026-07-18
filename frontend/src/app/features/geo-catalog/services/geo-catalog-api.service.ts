import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { API_CONFIG } from '../../../core/api/api.config';

export interface GeoEntry {
  id: string;
  type: string;
  code: string;
  name: string;
  countryCode: string;
  stateCode: string;
  category: string;
  isoCode: string;
  latitude: number | null;
  longitude: number | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string | null;
}

export interface GeoListResponse {
  items: GeoEntry[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface GeoResolveResponse {
  destinations: Record<number, string>;
  countries: Record<number, string>;
  sites: Record<number, string>;
}

@Injectable({ providedIn: 'root' })
export class GeoCatalogApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get baseUrl() {
    return `${this.apiConfig.baseUrl}/geo`;
  }

  listEntries(type?: string, countryCode?: string, q?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (type) params = params.set('type', type);
    if (countryCode) params = params.set('country_code', countryCode);
    if (q) params = params.set('q', q);
    return this.http.get<GeoListResponse>(`${this.baseUrl}/entries`, { params, withCredentials: true });
  }

  getEntry(entryId: string) {
    return this.http.get<GeoEntry>(`${this.baseUrl}/entries/${entryId}`, { withCredentials: true });
  }

  createEntry(payload: {
    type: string;
    code: string;
    name: string;
    country_code?: string;
    state_code?: string;
    category?: string;
    iso_code?: string;
    latitude?: number | null;
    longitude?: number | null;
  }) {
    return this.http.post<GeoEntry>(`${this.baseUrl}/entries`, payload, { withCredentials: true });
  }

  updateEntry(
    entryId: string,
    payload: {
      name?: string;
      country_code?: string;
      state_code?: string;
      category?: string;
      iso_code?: string;
      latitude?: number | null;
      longitude?: number | null;
      is_active?: boolean;
    },
  ) {
    return this.http.put<GeoEntry>(`${this.baseUrl}/entries/${entryId}`, payload, { withCredentials: true });
  }

  deleteEntry(entryId: string) {
    return this.http.delete<{ ok: boolean; message: string }>(`${this.baseUrl}/entries/${entryId}`, {
      withCredentials: true,
    });
  }

  resolveIds(payload: { destination_ids?: number[]; country_ids?: number[]; site_ids?: number[] }) {
    return this.http.post<GeoResolveResponse>(`${this.baseUrl}/resolve`, payload, { withCredentials: true });
  }

  listVisitorCountries() {
    return this.http.get<{ items: { visitor_location_country_id: number; country_display_name: string }[] }>(
      `${this.baseUrl}/visitor-countries`,
      { withCredentials: true }
    );
  }

  updateVisitorCountry(countryId: number, displayName: string) {
    return this.http.put<{ ok: boolean; message: string }>(
      `${this.baseUrl}/visitor-countries/${countryId}`,
      { country_display_name: displayName },
      { withCredentials: true }
    );
  }

  listVisitorDestinations() {
    return this.http.get<{ items: { srch_destination_id: number; destination_display_name: string }[] }>(
      `${this.baseUrl}/visitor-destinations`,
      { withCredentials: true }
    );
  }

  updateVisitorDestination(destId: number, displayName: string) {
    return this.http.put<{ ok: boolean; message: string }>(
      `${this.baseUrl}/visitor-destinations/${destId}`,
      { destination_display_name: displayName },
      { withCredentials: true }
    );
  }

  listVisitorSites() {
    return this.http.get<{ items: { site_id: number; site_display_name: string }[] }>(
      `${this.baseUrl}/visitor-sites`,
      { withCredentials: true }
    );
  }

  updateVisitorSite(siteId: number, displayName: string) {
    return this.http.put<{ ok: boolean; message: string }>(
      `${this.baseUrl}/visitor-sites/${siteId}`,
      { site_display_name: displayName },
      { withCredentials: true }
    );
  }

  listVisitorHotels() {
    return this.http.get<{ items: { prop_id: number; hotel_name: string }[] }>(
      `${this.baseUrl}/visitor-hotels`,
      { withCredentials: true }
    );
  }

  updateVisitorHotel(propId: number, hotelName: string) {
    return this.http.put<{ ok: boolean; message: string }>(
      `${this.baseUrl}/visitor-hotels/${propId}`,
      { hotel_name: hotelName },
      { withCredentials: true }
    );
  }
}
