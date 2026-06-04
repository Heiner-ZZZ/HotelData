import type {
  DashboardArrivalDto,
  DashboardQuickStatsDto,
  DashboardRevenuePointDto,
  EditPropertyResponseDto,
  PropertiesDashboardResponseDto,
  PropertyDetailResponseDto,
  PropertiesListResponseDto
} from '../models/properties.dto';
import type {
  DashboardArrival,
  DashboardQuickStats,
  DashboardRevenuePoint,
  EditPropertyViewModel,
  PropertiesDashboardViewModel,
  PropertyDetailViewModel,
  PropertyListItem,
  PropertiesListViewModel
} from '../models/properties.model';

function mapOperationalChecks(operational?: {
  policies_configured?: boolean;
  rooms_configured?: boolean;
  rates_configured?: boolean;
  inventory_configured?: boolean;
  content_configured?: boolean;
  images_configured?: boolean;
  promotions_active?: boolean;
}) {
  return [
    { label: 'Políticas', ready: operational?.policies_configured ?? false },
    { label: 'Habitaciones', ready: operational?.rooms_configured ?? false },
    { label: 'Tarifas', ready: operational?.rates_configured ?? false },
    { label: 'Inventario', ready: operational?.inventory_configured ?? false },
    { label: 'Contenido/Imágenes', ready: (operational?.content_configured ?? false) || (operational?.images_configured ?? false) },
    { label: 'Promociones', ready: operational?.promotions_active ?? false }
  ];
}

function mapPropertyListItem(item: PropertiesListResponseDto['items'][number]): PropertyListItem {
  return {
    propId: item.prop_id,
    displayName: item.display_name,
    countryDisplayName: item.country_display_name,
    location: item.location,
    starsLabel: item.prop_starrating?.toString() || 'N/D',
    reviewScoreLabel: item.review_score_label || 'N/D',
    yieldScore: item.yield_score ?? 0,
    status: item.status ?? 'Operational',
    syncStatus: item.sync_status ?? 'SYNC_ACTIVE',
    syncLatencyMs: item.sync_latency_ms ?? 0,
    unitCount: item.unit_count ?? 0,
    manualOverride: item.manual_override ?? false,
    profileBadge: item.profile_badge || (item.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    operationalScore: item.operational?.operational_score ?? 0,
    operationalChecks: mapOperationalChecks(item.operational),
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
    hotelName: dto.hotel.hotel_name || dto.hotel.display_name,
    countryDisplayName: dto.hotel.country_display_name || 'N/D',
    manualOverride: dto.hotel.manual_override ?? false,
    profileBadge: dto.hotel.profile_badge || (dto.hotel.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    originalGeneratedName: dto.hotel.original_generated_name || dto.hotel.display_name || `Hotel Partner ${dto.hotel.prop_id}`,
    operationalScore: dto.hotel.operational?.operational_score ?? 0,
    operationalChecks: mapOperationalChecks(dto.hotel.operational),
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

function mapQuickStats(dto: DashboardQuickStatsDto): DashboardQuickStats {
  return {
    occupancyRate: dto.occupancy_rate,
    occupancyTrend: dto.occupancy_trend,
    totalRevenueMtd: dto.total_revenue_mtd,
    revenueTrend: dto.revenue_trend,
    pendingCheckins: dto.pending_checkins,
    dataHealthScore: dto.data_health_score
  };
}

function mapRevenuePoint(dto: DashboardRevenuePointDto): DashboardRevenuePoint {
  return { period: dto.period, revenue: dto.revenue };
}

function mapArrival(dto: DashboardArrivalDto): DashboardArrival {
  return {
    guestName: dto.guest_name,
    initials: dto.initials,
    roomType: dto.room_type,
    nights: dto.nights,
    arrivalTime: dto.arrival_time,
    statusTag: dto.status_tag
  };
}

export function mapEditPropertyResponse(dto: EditPropertyResponseDto): EditPropertyViewModel {
  const cp = dto.content_page ?? {};
  const pol = dto.policies ?? {};
  const profile = dto.profile ?? {
    prop_id: dto.hotel.prop_id,
    hotel_name: dto.hotel.hotel_name || dto.hotel.display_name,
    display_name: dto.hotel.display_name,
    display_country_label: dto.hotel.country_display_name,
    description: dto.hotel.description ?? cp.description ?? '',
    original_generated_name: dto.hotel.original_generated_name ?? dto.hotel.display_name,
    manual_override: dto.hotel.manual_override ?? false,
    name_source: dto.hotel.name_source ?? 'generated_from_id',
    profile_badge: dto.hotel.profile_badge ?? (dto.hotel.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    updated_by: '',
    updated_at: ''
  };
  return {
    propId: dto.hotel.prop_id,
    hotelName: profile.hotel_name,
    displayName: profile.display_name,
    countryDisplayName: profile.display_country_label || dto.hotel.country_display_name,
    originalGeneratedName: profile.original_generated_name || dto.hotel.display_name || `Hotel Partner ${dto.hotel.prop_id}`,
    manualOverride: profile.manual_override ?? false,
    profileBadge: profile.profile_badge || (profile.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    updatedBy: profile.updated_by ?? '',
    updatedAt: profile.updated_at ?? '',
    description: profile.description ?? cp.description ?? dto.hotel.description ?? '',
    policies: {
      checkInTime: pol['check_in_time'] ?? '',
      checkOutTime: pol['check_out_time'] ?? '',
      cancellationPolicy: pol['cancellation_policy'] ?? '',
      petPolicy: pol['pet_policy'] ?? 'false',
      childrenPolicy: pol['children_policy'] ?? '',
      extraBedPolicy: pol['extra_bed_policy'] ?? '',
      paymentPolicy: pol['payment_policy'] ?? '',
      houseRules: pol['house_rules'] ?? '',
    },
    images: (dto.images ?? []).map((i: { image_url: string; title: string }) => ({ imageUrl: i.image_url, title: i.title })),
    amenities: dto.amenities?.active_amenities ?? [],
    amenityCatalog: dto.amenities?.catalog ?? [],
  };
}

export function mapPropertiesDashboardResponse(dto: PropertiesDashboardResponseDto): PropertiesDashboardViewModel {
  return {
    quickStats: mapQuickStats(dto.quick_stats),
    revenueChart: dto.revenue_chart.map(mapRevenuePoint),
    arrivalsToday: dto.arrivals_today.map(mapArrival),
    properties: mapPropertiesListResponse(dto.properties)
  };
}
