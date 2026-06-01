import type { HotelSearchResponseDto } from '../models/hotel-search.dto';
import type { HotelSearchResult, HotelSearchViewModel } from '../models/hotel-search.model';

function mapHotelSearchItems(dto: HotelSearchResponseDto): HotelSearchResult[] {
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

export function mapHotelSearchResponse(dto: HotelSearchResponseDto): HotelSearchViewModel {
  return {
    items: mapHotelSearchItems(dto),
    total: dto.total,
    page: dto.page,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
    sourceCollection: dto.source_collection,
    startIndex: dto.start_index,
    endIndex: dto.end_index,
    filters: {
      destination: dto.filters.destination,
      minPrice: dto.filters.min_price,
      maxPrice: dto.filters.max_price,
      minStars: dto.filters.min_stars,
      promotion: dto.filters.promotion,
      adults: dto.filters.adults,
      children: dto.filters.children,
      rooms: dto.filters.rooms
    }
  };
}
