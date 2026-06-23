import type { HotelCompareDto, HotelCompareItemDto } from '../models/hotel-compare.dto';
import type { HotelCompareData, HotelCompareItem, HotelCompareRoomType } from '../models/hotel-compare.model';

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
    destinationLabels: dto.destination_labels ?? [],
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
