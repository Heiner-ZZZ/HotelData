import type { HotelDetailDto } from '../models/hotel-detail.dto';
import type { HotelDetailViewModel } from '../models/hotel-detail.model';

function displayValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return 'N/D';
  }
  return String(value);
}

export function mapHotelDetailResponse(dto: HotelDetailDto): HotelDetailViewModel {
  return {
    id: dto.prop_id,
    name: dto.hotel_label,
    location: dto.country_display_name,
    starsLabel: displayValue(dto.prop_starrating),
    reviewLabel: displayValue(dto.review_label),
    averagePrice: dto.avg_price_label,
    reservations: dto.reservations,
    clicks: dto.clicks,
    events: dto.events,
    promotions: dto.promotions,
    conversionRate: dto.conversion_rate,
    clickRate: dto.click_rate,
    sourceCollection: dto.source_collection,
    basicFacts: [
      { label: 'Prop ID', value: String(dto.prop_id) },
      { label: 'País / mercado', value: dto.country_display_name },
      { label: 'Estrellas', value: displayValue(dto.prop_starrating) },
      { label: 'Review score', value: displayValue(dto.review_label) },
      { label: 'Eventos', value: String(dto.events) },
      { label: 'Promociones', value: String(dto.promotions) }
    ],
    topDestinations: dto.top_destinations.map((item) => ({
      label: item.destination_label,
      events: item.events,
      avgPriceLabel: item.avg_price_label
    })),
    topVisitorCountries: dto.top_visitor_countries.map((item) => ({
      id: item.visitor_location_country_id,
      label: item.country_label,
      events: item.events,
      reservations: item.reservations
    })),
    topSites: dto.top_sites.map((item) => ({
      id: item.site_id,
      label: item.site_label,
      events: item.events,
      clicks: item.clicks,
      reservations: item.reservations
    })),
    hotelRates: dto.hotel_rates.map((item) => ({
      date: item.date,
      plan: item.rate_plan_id,
      amountLabel: item.rate_amount_label,
      minStayLabel: displayValue(item.min_stay_nights)
    })),
    roomTypes: dto.room_types.map((item) => ({
      id: item.room_type_id,
      name: item.name,
      capacityLabel: `${displayValue(item.base_capacity)} base · ${displayValue(item.max_adults)} adultos · ${displayValue(item.max_children)} niños`,
      statusLabel: item.is_active ? 'Activa' : 'Inactiva'
    })),
    policies: dto.hotel_policies
      ? [
          { label: 'Check-in', value: displayValue(dto.hotel_policies.check_in_time) },
          { label: 'Check-out', value: displayValue(dto.hotel_policies.check_out_time) },
          { label: 'Mascotas', value: displayValue(dto.hotel_policies.pet_policy) },
          { label: 'Niños', value: displayValue(dto.hotel_policies.children_policy) }
        ]
      : [],
    cancellationPolicy: displayValue(dto.hotel_policies?.cancellation_policy),
    galleryImages: (dto.hotel_images || []).length > 0
      ? dto.hotel_images.map((img) => img.image_url)
      : [
          `https://picsum.photos/seed/${dto.prop_id}1/800/400`,
          `https://picsum.photos/seed/${dto.prop_id}2/800/400`,
          `https://picsum.photos/seed/${dto.prop_id}3/800/400`,
        ],
    description: dto.hotel_content?.description || '',
    highlights: dto.hotel_content?.highlights || '',
    amenitiesTags: (dto.hotel_content?.amenities_text || '').split(',').map((s) => s.trim()).filter(Boolean),
    reviews: (dto.reviews || []).map((r) => ({
      reviewerName: r.reviewer_name || 'Anónimo',
      score: r.review_score || 0,
      text: r.review_text || '',
      date: r.created_at || ''
    }))
  };
}
