import type { HotelCompareDto, HotelCompareItemDto } from '../models/hotel-compare.dto';
import type { HotelCompareData, HotelCompareItem, HotelCompareRoomType, PolicyItem } from '../models/hotel-compare.model';

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return 'N/D';
  }
  return String(value);
}

function mapPolicies(policies: Record<string, unknown>): PolicyItem[] {
  if (!policies || Object.keys(policies).length === 0) {
    return [];
  }
  return [
    { label: 'Check-in', value: displayValue(policies['check_in_time']) },
    { label: 'Check-out', value: displayValue(policies['check_out_time']) },
    { label: 'Mascotas', value: displayValue(policies['pet_policy']) },
    { label: 'Niños', value: displayValue(policies['children_policy']) },
    { label: 'Camas extra', value: displayValue(policies['extra_bed_policy']) },
    { label: 'Pagos', value: displayValue(policies['payment_policy']) },
    { label: 'Reglas', value: displayValue(policies['house_rules']) },
  ].filter(p => p.value !== 'N/D');
}

function mapCancellationPolicy(policies: Record<string, unknown>): string {
  return displayValue(policies['cancellation_policy']);
}

function mapRoomType(dto: HotelCompareItemDto['room_types'][number]): HotelCompareRoomType {
  return {
    roomTypeId: dto.room_type_id,
    name: dto.name,
    maxAdults: dto.max_adults,
    maxChildren: dto.max_children,
    baseCapacity: dto.base_capacity,
    description: dto.description,
  };
}

function mapItem(dto: HotelCompareItemDto): HotelCompareItem {
  return {
    propId: dto.prop_id,
    hotelName: dto.hotel_name,
    displayName: dto.display_name,
    propStarrating: dto.prop_starrating,
    propReviewScore: dto.prop_review_score,
    imageUrl: dto.image_url,
    amenitiesText: dto.amenities_text,
    roomTypes: (dto.room_types ?? []).map(mapRoomType),
    policies: dto.policies ?? {},
    mappedPolicies: mapPolicies(dto.policies ?? {}),
    cancellationPolicy: mapCancellationPolicy(dto.policies ?? {}),
    destinationLabels: dto.destination_labels ?? [],
    latitude: dto.latitude,
    longitude: dto.longitude,
    minNightlyRate: dto.min_nightly_rate,
    minNightlyRateLabel: dto.min_nightly_rate_label,
    totalEstimated: dto.total_estimated,
    totalEstimatedLabel: dto.total_estimated_label,
  };
}

export function mapHotelCompareResponse(dto: HotelCompareDto): HotelCompareData {
  return {
    items: (dto.items ?? []).map(mapItem),
  };
}
