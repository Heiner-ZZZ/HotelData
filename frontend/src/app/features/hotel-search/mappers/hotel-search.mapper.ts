import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters, HotelSearchPageData, HotelSearchResult } from '../models/hotel-search.model';

export function mapHotelSearchItems(dto: HotelSearchDto): HotelSearchResult[] {
  return dto.items.map((item) => ({
    id: item.prop_id,
    name: item.hotel_label,
    location: item.country_display_name,
    stars: item.prop_starrating,
    reviewLabel: item.review_label,
    hasPromotion: item.has_promotion,
    avgPriceLabel: item.avg_price_label,
    reservations: item.reservations,
    clicks: item.clicks,
    conversionRate: item.conversion_rate,
    destinationLabels: item.destination_labels
  }));
}

export function mapHotelSearchResponse(dto: HotelSearchDto): HotelSearchPageData {
  return {
    items: mapHotelSearchItems(dto),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
    sourceCollection: dto.source_collection,
    filters: mapHotelSearchFilters(dto),
    startIndex: dto.start_index,
    endIndex: dto.end_index
  };
}

export function createHotelSearchFilters(
  partial: Partial<HotelSearchFilters> = {}
): HotelSearchFilters {
  return {
    destination: partial.destination ?? '',
    minPrice: partial.minPrice ?? '',
    maxPrice: partial.maxPrice ?? '',
    minStars: partial.minStars ?? '',
    promotion: partial.promotion ?? '',
    adults: partial.adults ?? '',
    children: partial.children ?? '',
    rooms: partial.rooms ?? '',
    page: partial.page ?? 1
  };
}

export function mapHotelSearchFilters(dto: Pick<HotelSearchDto, 'filters' | 'page'>): HotelSearchFilters {
  return createHotelSearchFilters({
    destination: dto.filters.destination,
    minPrice: dto.filters.min_price,
    maxPrice: dto.filters.max_price,
    minStars: dto.filters.min_stars,
    promotion: (dto.filters.promotion as HotelSearchFilters['promotion']) || '',
    adults: dto.filters.adults,
    children: dto.filters.children,
    rooms: dto.filters.rooms,
    page: dto.page
  });
}
