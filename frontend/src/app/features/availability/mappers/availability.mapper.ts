import type { AvailabilityDto, ManagementPropertiesDto } from '../models/availability.dto';
import type {
  AvailabilityBlackoutItem,
  AvailabilityInventoryItem,
  AvailabilityPropertyOption,
  AvailabilityRoomType,
  AvailabilityViewModel,
  PropertyOptionsPage
} from '../models/availability.model';

export function mapAvailability(dto: AvailabilityDto): AvailabilityViewModel {
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    roomTypes: dto.room_types.map(mapRoomType),
    inventoryItems: dto.inventory_items.map(mapInventoryItem),
    availabilityBlocks: (dto.availability_blocks ?? []).map(mapBlackoutItem),
    blackoutItems: dto.blackout_items.map(mapBlackoutItem)
  };
}

export function mapAvailabilityPropertyOptions(dto: ManagementPropertiesDto): PropertyOptionsPage {
  return {
    items: dto.properties.map((item) => ({
      propId: item.prop_id,
      label: item.display_name || `Hotel ${item.prop_id}`
    })),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    hasNext: dto.has_next
  };
}

function mapRoomType(item: AvailabilityDto['room_types'][number]): AvailabilityRoomType {
  return {
    id: item.room_type_id,
    name: item.name,
    capacityLabel: item.capacity_label,
    isActive: item.is_active
  };
}

function mapInventoryItem(item: AvailabilityDto['inventory_items'][number]): AvailabilityInventoryItem {
  return {
    date: item.date,
    roomTypeName: item.room_type_name,
    totalRooms: item.total_rooms,
    availableRooms: item.available_rooms,
    blockedRooms: item.blocked_rooms,
    occupancyLabel: item.occupancy_label,
    occupancyPct: item.occupancy_pct ?? 0
  };
}

function mapBlackoutItem(item: AvailabilityDto['blackout_items'][number]): AvailabilityBlackoutItem {
  return {
    roomTypeId: item.room_type_id,
    rangeLabel: item.range_label,
    blockedRooms: item.blocked_rooms,
    reason: item.reason || 'Sin razón'
  };
}
