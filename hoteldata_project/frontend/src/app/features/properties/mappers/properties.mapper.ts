import type { PropertyDetailResponseDto, PropertiesListResponseDto } from '../models/properties.dto';
import type { PropertyDetailViewModel, PropertyListItem, PropertiesListViewModel } from '../models/properties.model';

function mapPropertyListItem(item: PropertiesListResponseDto['items'][number]): PropertyListItem {
  return {
    propId: item.prop_id,
    displayName: item.display_name,
    countryDisplayName: item.country_display_name,
    starsLabel: item.prop_starrating?.toString() || 'N/D',
    reviewScoreLabel: item.review_score_label || 'N/D',
    performance: {
      searches: item.performance.searches,
      clicks: item.performance.clicks,
      reservations: item.performance.reservations,
      grossRevenueLabel: item.performance.gross_revenue_label
    }
  };
}

export function mapPropertiesListResponse(dto: PropertiesListResponseDto): PropertiesListViewModel {
  return {
    items: dto.items.map(mapPropertyListItem),
    query: dto.query,
    page: dto.page,
    totalPages: dto.total_pages,
    total: dto.total,
    startIndex: dto.start_index,
    endIndex: dto.end_index,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next
  };
}

export function mapPropertyDetailResponse(dto: PropertyDetailResponseDto): PropertyDetailViewModel {
  return {
    propId: dto.hotel.prop_id,
    displayName: dto.hotel.display_name,
    heroMetrics: [
      {
        label: 'Ingresos brutos',
        value: `$${dto.performance.gross_revenue_label}`,
        detail: `Fuente: ${dto.performance.source_collection}`
      },
      {
        label: 'Reservas',
        value: String(dto.performance.reservations),
        detail: `${dto.performance.conversion_rate}% conversion`
      },
      {
        label: 'Clicks',
        value: String(dto.performance.clicks),
        detail: `${dto.performance.click_rate}% click rate`
      }
    ],
    profileFacts: [
      { label: 'Prop ID', value: String(dto.hotel.prop_id) },
      { label: 'Pais / mercado', value: dto.hotel.country_display_name || 'N/D' },
      { label: 'Estrellas', value: dto.hotel.prop_starrating?.toString() || 'N/D' },
      { label: 'Review score', value: dto.hotel.review_score_label || 'N/D' },
      { label: 'Marca', value: dto.hotel.prop_brand_bool ? 'Si' : 'No' },
      { label: 'Location score', value: dto.hotel.prop_location_score1?.toString() || 'N/D' }
    ],
    masterFacts: [
      { label: 'Hotel code', value: dto.master_hotel.hotel_code || 'N/D' },
      { label: 'Hotel name', value: dto.master_hotel.hotel_name || dto.hotel.display_name },
      { label: 'Description', value: dto.master_hotel.description || dto.hotel.description || 'N/D' },
      {
        label: 'Rating',
        value: dto.master_hotel.rating?.toString() || dto.hotel.prop_starrating?.toString() || 'N/D'
      }
    ]
  };
}
