import type { HotelDetailDto } from '../models/hotel-detail.dto';
import type { HotelDetailViewModel } from '../models/hotel-detail.model';
import { placeholderImageUrl } from '../../../shared/utils/placeholder-image.util';

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
    minRateLabel: dto.min_rate_label || dto.avg_price_label,
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
    hotelRooms: (dto.hotel_rooms || []).map((item) => ({
      hotelRoomId: item.hotel_room_id,
      roomNumber: item.room_number || '',
      roomLabel: item.room_label,
      roomTypeId: item.room_type_id,
      floor: item.floor || '',
      isActive: item.is_active,
    })),
    roomTypes: dto.room_types.map((item) => ({
      id: item.room_type_id,
      name: item.name,
      capacityLabel: `${displayValue(item.base_capacity)} base · ${displayValue(item.max_adults)} adultos · ${displayValue(item.max_children)} niños`,
      statusLabel: item.is_active ? 'Activa' : 'Inactiva',
      description: item.description || '',
      imageUrl: item.image_url || '',
      features: (item.features || []).reduce<string[]>((acc, f) => {
        if (typeof f === 'string') { if (f.trim()) acc.push(f.trim()); return acc; }
        const maybe = f as { label?: unknown } | null;
        if (maybe?.label && typeof maybe.label === 'string' && maybe.label.trim()) {
          acc.push(maybe.label.trim());
        }
        return acc;
      }, []),
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
          placeholderImageUrl(`${dto.prop_id}1`, 800, 400),
          placeholderImageUrl(`${dto.prop_id}2`, 800, 400),
          placeholderImageUrl(`${dto.prop_id}3`, 800, 400),
        ],
    description: dto.hotel_content?.description || '',
    highlights: dto.hotel_content?.highlights || '',
    amenitiesTags: (dto.hotel_content?.amenities_text || '').split(',').map((s) => s.trim()).filter(Boolean),
    facilities: {
      meetingRooms: dto.hotel_content?.facilities?.meeting_rooms ?? 0,
      fiberOptic: dto.hotel_content?.facilities?.fiber_optic ?? '—',
      concierge24h: dto.hotel_content?.facilities?.concierge_24h ?? false,
      gym: dto.hotel_content?.facilities?.gym ?? false,
      pool: dto.hotel_content?.facilities?.pool ?? false,
      parking: dto.hotel_content?.facilities?.parking ?? false,
      evCharging: dto.hotel_content?.facilities?.ev_charging ?? false,
      restaurant: dto.hotel_content?.facilities?.restaurant ?? false,
      businessCenter: dto.hotel_content?.facilities?.business_center ?? false,
    },
    latitude: dto.hotel_content?.latitude ?? 0,
    longitude: dto.hotel_content?.longitude ?? 0,
    reviewCount: dto.review_count ?? 0,
    reviews: (dto.reviews || []).map((r) => ({
      reviewerName: r.reviewer_name || 'Anónimo',
      score: r.review_score || 0,
      text: r.review_text || '',
      date: r.created_at || ''
    }))
  };
}
