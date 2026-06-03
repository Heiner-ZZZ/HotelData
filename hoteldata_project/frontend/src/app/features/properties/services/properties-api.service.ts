import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapEditPropertyResponse, mapPropertiesDashboardResponse, mapPropertyDetailResponse, mapPropertiesListResponse } from '../mappers/properties.mapper';
import type { EditPropertyResponseDto, PropertiesDashboardResponseDto, PropertyDetailResponseDto, PropertiesListResponseDto } from '../models/properties.dto';

@Injectable({
  providedIn: 'root'
})
export class PropertiesApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getProperties(query: string, page: number) {
    let params = new HttpParams().set('page', page);
    if (query.trim()) {
      params = params.set('q', query.trim());
    }

    return this.http
      .get<PropertiesListResponseDto>(`${this.apiConfig.baseUrl}/management/properties`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapPropertiesListResponse(dto)));
  }

  getPropertyDetail(propId: number) {
    return this.http
      .get<PropertyDetailResponseDto>(`${this.apiConfig.baseUrl}/management/properties/${propId}`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapPropertyDetailResponse(dto)));
  }

  getDashboard(query: string = '', page: number = 1) {
    let params = new HttpParams().set('page', page);
    if (query.trim()) {
      params = params.set('q', query.trim());
    }

    return this.http
      .get<PropertiesDashboardResponseDto>(`${this.apiConfig.baseUrl}/management/properties/dashboard`, {
        params,
        withCredentials: true
      })
      .pipe(map((dto) => mapPropertiesDashboardResponse(dto)));
  }

  getEditProfile(propId: number) {
    return this.http
      .get<EditPropertyResponseDto>(`${this.apiConfig.baseUrl}/management/properties/${propId}/edit`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapEditPropertyResponse(dto)));
  }

  saveProfile(
    propId: number,
    profile: {
      hotel_name: string;
      display_name: string;
      description: string;
      display_country_label: string;
      reason?: string;
    }
  ) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/properties/${propId}/profile`,
      profile,
      { withCredentials: true }
    );
  }

  saveContent(propId: number, description: string) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/properties/${propId}/content`,
      { description },
      { withCredentials: true }
    );
  }

  savePolicies(propId: number, policies: Record<string, string>) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/policies`,
      { prop_id: propId, ...policies },
      { withCredentials: true }
    );
  }

  saveAmenities(propId: number, activeAmenities: string[]) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/management/amenities`,
      { prop_id: propId, active_amenities: activeAmenities },
      { withCredentials: true }
    );
  }

  addImage(propId: number, imageUrl: string, title: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/management/properties/${propId}/images`,
      { image_url: imageUrl, title },
      { withCredentials: true }
    );
  }

  deleteImage(propId: number, imageUrl: string) {
    return this.http.delete(
      `${this.apiConfig.baseUrl}/management/properties/${propId}/images`,
      { params: new HttpParams().set('image_url', imageUrl), withCredentials: true }
    );
  }
}
