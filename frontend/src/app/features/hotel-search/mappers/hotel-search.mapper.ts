import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters, HotelSearchPageData, HotelSearchResult } from '../models/hotel-search.model';

export function mapHotelSearchItems(dto: HotelSearchDto): HotelSearchResult[] {
  return dto.items.map((item) => ({
    id: item.prop_id,
    name: item.hotel_name,
    displayName: item.display_name,
    stars: item.prop_starrating,
    reviewScore: item.prop_review_score,
    imageUrl: item.image_url,
    destinationLabels: item.destination_labels,
    matchedRoomType: item.matched_room_type
      ? {
          roomTypeId: item.matched_room_type.room_type_id,
          name: item.matched_room_type.name,
          maxAdults: item.matched_room_type.max_adults,
          maxChildren: item.matched_room_type.max_children,
          baseCapacity: item.matched_room_type.base_capacity,
        }
      : null,
    minNightlyRate: item.min_nightly_rate,
    minNightlyRateLabel: item.min_nightly_rate_label,
    totalEstimated: item.total_estimated,
    totalEstimatedLabel: item.total_estimated_label,
    availableRoomTypesCount: item.available_room_types_count,
    selected: false,
  }));
}

export function mapHotelSearchResponse(dto: HotelSearchDto, filters: HotelSearchFilters): HotelSearchPageData {
  return {
    items: mapHotelSearchItems(dto),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
    filters,
    alternativeDestinations: dto.alternative_destinations?.map((d) => ({
      id: d.id,
      displayName: d.display_name,
    })),
  };
}

export function createHotelSearchFilters(
  partial: Partial<HotelSearchFilters> = {}
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
    amenities: partial.amenities ?? '',
    amenitiesMode: partial.amenitiesMode ?? 'or',
    sortBy: partial.sortBy ?? 'price',
    compareIds: partial.compareIds ?? [],
    page: partial.page ?? 1,
  };
}
