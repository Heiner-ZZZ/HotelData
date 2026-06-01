import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchResult } from '../models/hotel-search.model';

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
