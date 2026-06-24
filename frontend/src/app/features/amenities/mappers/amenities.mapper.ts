import type { AmenitiesDto, AmenitiesOptionsDto, AmenitiesSaveDto } from '../models/amenities.dto';
import type { AmenityCategoryViewModel, AmenitiesPropertyOption, AmenitiesViewModel, RoomTypeOption } from '../models/amenities.model';

export function mapAmenities(dto: AmenitiesDto): AmenitiesViewModel {
  const roomAmenities: Record<string, string[]> = {};
  if (dto.room_amenities) {
    for (const [key, val] of Object.entries(dto.room_amenities)) {
      roomAmenities[key] = val.active_amenities ?? [];
    }
  }
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    activeAmenities: dto.amenities.active_amenities ?? [],
    contentDescription: dto.content_page?.description || 'Sin descripción cargada',
    imageCount: dto.images?.length ?? 0,
    facilityCount: dto.facilities?.length ?? 0,
    categories: dto.amenities.catalog.map(mapAmenityCategory),
    roomTypes: (dto.room_types ?? [])
      .filter((rt) => rt.is_active)
      .map((rt) => ({
        roomTypeId: rt.room_type_id,
        name: rt.name,
        capacityLabel: rt.capacity_label,
      })),
    roomAmenities,
  };
}

export function mapAmenitiesOptions(dto: AmenitiesOptionsDto): AmenitiesPropertyOption[] {
  return dto.properties.map((item) => ({
    propId: item.prop_id,
    label: item.display_name || `Hotel ${item.prop_id}`
  }));
}

export function mapAmenityCategory(item: AmenitiesDto['amenities']['catalog'][number]): AmenityCategoryViewModel {
  return {
    category: item.category,
    items: item.items.map((entry) => ({
      label: entry.label,
      active: entry.active
    }))
  };
}

export function mapAmenitiesPayload(propId: number, activeAmenities: string[], roomTypeId = ''): AmenitiesSaveDto {
  return {
    prop_id: propId,
    active_amenities: activeAmenities,
    amenities_text: activeAmenities.join(', '),
    ...(roomTypeId ? { room_type_id: roomTypeId } : {}),
  };
}
