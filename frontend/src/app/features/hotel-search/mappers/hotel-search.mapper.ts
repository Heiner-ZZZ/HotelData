import { isDevMode } from '@angular/core';

import { toast } from '../../../core/toast/toast.service';
import type { HotelSearchDto, HotelSearchItemDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters, HotelSearchPageData, HotelSearchResult } from '../models/hotel-search.model';

let lastDriftToastAt = 0;
const DRIFT_TOAST_MIN_INTERVAL_MS = 6000;

function safeToast(text: string): void {
  if (isDevMode() && Date.now() - lastDriftToastAt > DRIFT_TOAST_MIN_INTERVAL_MS) {
    lastDriftToastAt = Date.now();
    toast(text, 'error', 6000);
  }
}

function nonEmptyString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

function mapRoomType(item: HotelSearchItemDto['matched_room_type']): HotelSearchResult['matchedRoomType'] {
  if (!item) return null;
  return {
    roomTypeId: item.room_type_id,
    name: item.name,
    maxAdults: item.max_adults,
    maxChildren: item.max_children,
    baseCapacity: item.base_capacity,
  };
}

/** Maps both the operational availability item and the legacy analytics item. */
export function mapHotelSearchItems(dto: HotelSearchDto): HotelSearchResult[] {
  if (!Array.isArray(dto.items)) {
    console.error('[hotel-search.mapper] Response is missing the `items` array. Got:', dto);
    safeToast('HotelData: la API no devolvió una lista válida de hoteles.');
    return [];
  }

  let missingNameCount = 0;
  const mapped = dto.items
    .filter((item) => {
      const valid = Number.isInteger(item?.prop_id) && item.prop_id > 0;
      if (!valid) {
        console.error('[hotel-search.mapper] Dropped item with invalid prop_id:', item);
        safeToast('HotelData: la API devolvió un hotel inválido.');
      }
      return valid;
    })
    .map((item) => {
      const name = nonEmptyString(item.hotel_name, item.display_name, item.hotel_label);
      if (!name) missingNameCount++;
      const resolvedName = name ?? `Hotel ${item.prop_id}`;
      const displayName = nonEmptyString(item.display_name, item.hotel_name, item.hotel_label) ?? resolvedName;
      const destinations = Array.isArray(item.destination_labels) ? item.destination_labels : [];
      const generalAmenities = Array.isArray(item.general_amenities)
        ? item.general_amenities.filter((label): label is string => typeof label === 'string' && label.trim().length > 0).slice(0, 4)
        : [];

      return {
        id: item.prop_id,
        name: resolvedName,
        displayName,
        stars: item.prop_starrating ?? null,
        reviewScore: item.prop_review_score ?? null,
        imageUrl: item.image_url ?? null,
        destinationLabels: destinations,
        generalAmenities,
        matchedRoomType: mapRoomType(item.matched_room_type),
        minNightlyRate: item.min_nightly_rate ?? null,
        minNightlyRateLabel: item.min_nightly_rate_label ?? null,
        totalEstimated: item.total_estimated ?? null,
        totalEstimatedLabel: item.total_estimated_label ?? null,
        minAvailableRooms: item.min_available_rooms ?? null,
        availableRoomTypesCount: item.available_room_types_count ?? null,
        selected: false,
      };
    });

  if (missingNameCount > 0) {
    console.warn(`[hotel-search.mapper] ${missingNameCount} hotel(s) arrived without a display name.`);
  }

  return mapped;
}

export function mapHotelSearchResponse(dto: HotelSearchDto, filters: HotelSearchFilters): HotelSearchPageData {
  const alternatives = Array.isArray(dto.alternative_destinations)
    ? dto.alternative_destinations.map((item) => ({
      id: item.id,
      displayName: item.display_name,
    }))
    : [];

  if (!Array.isArray(dto.alternative_destinations)) {
    console.warn('[hotel-search.mapper] Missing `alternative_destinations`; using an empty list.');
  }

  return {
    items: mapHotelSearchItems(dto),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    totalIsEstimate: dto.total_is_estimate ?? false,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
    filters,
    alternativeDestinations: alternatives,
  };
}

export function createHotelSearchFilters(
  partial: Partial<HotelSearchFilters> = {},
): HotelSearchFilters {
  return {
    destination: partial.destination ?? '',
    checkIn: partial.checkIn ?? '',
    checkOut: partial.checkOut ?? '',
    adults: partial.adults ?? '1',
    children: partial.children ?? '0',
    rooms: partial.rooms ?? '1',
    minPrice: partial.minPrice ?? '',
    maxPrice: partial.maxPrice ?? '',
    minStars: partial.minStars ?? '',
    amenities: partial.amenities ?? [],
    amenitiesMode: partial.amenitiesMode ?? 'or',
    sortBy: partial.sortBy ?? 'price',
    compareIds: partial.compareIds ?? [],
    page: partial.page ?? 1,
  };
}
