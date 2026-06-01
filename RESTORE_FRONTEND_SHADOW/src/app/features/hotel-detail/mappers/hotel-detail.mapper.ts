import type { HotelDetailDto } from '../models/hotel-detail.dto';
import type { HotelDetailViewModel } from '../models/hotel-detail.model';

export function mapHotelDetailResponse(dto: HotelDetailDto): HotelDetailViewModel {
  return {
    propId: dto.prop_id,
    hotelLabel: dto.hotel_label,
    heroMetrics: [
      {
        label: 'Precio promedio',
        value: `$${dto.avg_price_label}`,
        detail: `Fuente: ${dto.source_collection}`
      },
      {
        label: 'Reservas',
        value: String(dto.reservations),
        detail: `${dto.conversion_rate}% de conversion`
      },
      {
        label: 'Clicks',
        value: String(dto.clicks),
        detail: `${dto.click_rate}% de click rate`
      }
    ],
    basicFacts: [
      { label: 'Prop ID', value: String(dto.prop_id) },
      { label: 'Pais / mercado', value: dto.country_display_name || 'N/D' },
      { label: 'Estrellas', value: dto.prop_starrating?.toString() || 'N/D' },
      { label: 'Review score', value: dto.review_label || 'N/D' },
      { label: 'Eventos', value: String(dto.events) },
      { label: 'Promociones', value: String(dto.promotions) }
    ],
    topDestinations: dto.top_destinations.map((item) => ({
      label: item.destination_label,
      events: item.events,
      avgPriceLabel: item.avg_price_label
    })),
    topVisitorCountries: dto.top_visitor_countries.map((item) => ({
      label: item.country_label,
      events: item.events,
      reservations: item.reservations,
      technicalId: item.visitor_location_country_id
    })),
    topSites: dto.top_sites.map((item) => ({
      label: item.site_label,
      events: item.events,
      clicks: item.clicks,
      reservations: item.reservations,
      technicalId: item.site_id
    })),
    hotelRates: dto.hotel_rates.map((item) => ({
      date: item.date,
      ratePlanId: String(item.rate_plan_id),
      rateAmountLabel: item.rate_amount_label,
      minStayNights: item.min_stay_nights?.toString() || 'N/D'
    })),
    roomTypes: dto.room_types.map((item) => ({
      name: item.name,
      roomTypeId: item.room_type_id,
      capacityLabel: `${item.base_capacity} base · ${item.max_adults} adultos · ${item.max_children} ninos`,
      statusLabel: item.is_active ? 'Activa' : 'Inactiva',
      isActive: item.is_active
    })),
    policies: dto.hotel_policies
      ? [
          { label: 'Check-in', value: dto.hotel_policies.check_in_time || 'N/D' },
          { label: 'Check-out', value: dto.hotel_policies.check_out_time || 'N/D' },
          { label: 'Mascotas', value: dto.hotel_policies.pet_policy || 'N/D' },
          { label: 'Ninos', value: dto.hotel_policies.children_policy || 'N/D' }
        ]
      : [],
    cancellationPolicy: dto.hotel_policies?.cancellation_policy || 'N/D'
  };
}
