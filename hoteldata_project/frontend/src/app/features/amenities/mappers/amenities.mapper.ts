import type { AmenitiesDto, AmenitiesOptionsDto, AmenitiesSaveDto } from '../models/amenities.dto';
import type { AmenityCategoryViewModel, AmenitiesPropertyOption, AmenitiesViewModel } from '../models/amenities.model';

export function mapAmenities(dto: AmenitiesDto): AmenitiesViewModel {
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    activeAmenities: dto.amenities.active_amenities ?? [],
    categories: dto.amenities.catalog.map(mapAmenityCategory)
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

export function mapAmenitiesPayload(propId: number, activeAmenities: string[]): AmenitiesSaveDto {
  return {
    prop_id: propId,
    active_amenities: activeAmenities,
    amenities_text: activeAmenities.join(', ')
  };
}
