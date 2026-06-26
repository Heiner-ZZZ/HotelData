import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import type { DestinationDto, PaginatedDestinationsDto, GeoDestinationDto, GeoHotelDto } from '../models/map.dto';
import type { Destination, PaginatedDestinations, GeoDestination, GeoHotel } from '../models/map.model';

function mapDestination(dto: DestinationDto): Destination {
  return {
    srchDestinationId: dto.srch_destination_id,
    destinationDisplayName: dto.destination_display_name,
    destinationName: dto.destination_name,
    visibleName: dto.visible_name,
    country: dto.country,
    city: dto.city,
    description: dto.description,
    latitude: dto.latitude,
    longitude: dto.longitude,
    destinationRegionLabel: dto.destination_region_label,
    active: dto.active,
  };
}

function mapPaginated(dto: PaginatedDestinationsDto): PaginatedDestinations {
  return {
    items: dto.items.map(mapDestination),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasNext: dto.has_next,
    hasPrev: dto.has_prev,
  };
}

function mapGeoDest(dto: GeoDestinationDto): GeoDestination {
  return {
    srchDestinationId: dto.srch_destination_id,
    destinationDisplayName: dto.destination_display_name,
    visibleName: dto.visible_name,
    country: dto.country,
    city: dto.city,
    latitude: dto.latitude,
    longitude: dto.longitude,
  };
}

function mapGeoHotel(dto: GeoHotelDto): GeoHotel {
  return {
    propId: dto.prop_id,
    hotelName: dto.hotel_name,
    displayName: dto.display_name,
    stars: dto.stars,
    reviewScore: dto.review_score,
    latitude: dto.latitude,
    longitude: dto.longitude,
    srchDestinationId: dto.srch_destination_id,
    destinationDisplayName: dto.destination_display_name,
  };
}

@Injectable({ providedIn: 'root' })
export class MapApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get baseUrl() {
    return `${this.apiConfig.baseUrl}/map`;
  }

  // ── Destinations CRUD ──

  getDestinations(page = 1, pageSize = 50, search?: string, hasGeo?: boolean) {
    let params = new HttpParams().set('page', String(page)).set('page_size', String(pageSize));
    if (search) params = params.set('search', search);
    if (hasGeo !== undefined) params = params.set('has_geo', String(hasGeo));
    return this.http
      .get<PaginatedDestinationsDto>(`${this.baseUrl}/destinations`, { params, withCredentials: true })
      .pipe(catchAuthError(), map(mapPaginated));
  }

  getDestination(destinationId: number) {
    return this.http
      .get<DestinationDto>(`${this.baseUrl}/destinations/${destinationId}`, { withCredentials: true })
      .pipe(catchAuthError(), map(mapDestination));
  }

  updateDestination(destinationId: number, data: {
    visible_name?: string;
    country?: string;
    city?: string;
    description?: string;
    latitude?: number | null;
    longitude?: number | null;
  }) {
    return this.http
      .put<DestinationDto>(`${this.baseUrl}/destinations/${destinationId}`, data, { withCredentials: true })
      .pipe(catchAuthError(), map(mapDestination));
  }

  // ── Geo data for maps ──

  getGeoDestinations() {
    return this.http
      .get<{ items: GeoDestinationDto[] }>(`${this.baseUrl}/geo/destinations`, { withCredentials: true })
      .pipe(catchAuthError(), map((res) => res.items.map(mapGeoDest)));
  }

  getGeoHotels() {
    return this.http
      .get<{ items: GeoHotelDto[] }>(`${this.baseUrl}/geo/hotels`, { withCredentials: true })
      .pipe(catchAuthError(), map((res) => res.items.map(mapGeoHotel)));
  }
}
