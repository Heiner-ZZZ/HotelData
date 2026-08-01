import { createHotelSearchFilters, mapHotelSearchResponse } from './hotel-search.mapper';
import type { HotelSearchDto } from '../models/hotel-search.dto';

describe('hotel-search.mapper', () => {
  it('maps operational availability fields used by the guest card', () => {
    const dto: HotelSearchDto = {
      items: [{
        prop_id: 137997,
        hotel_name: 'Hotel Costa Azul',
        display_name: 'Hotel Costa Azul',
        image_url: 'https://example.test/hotel.jpg',
        prop_starrating: 4,
        prop_review_score: 8.6,
        destination_labels: ['Madrid'],
        general_amenities: ['Wi-Fi', 'Piscina', 'Playa', 'Parking', 'Spa'],
        available_room_types_count: 2,
        matched_room_type: {
          room_type_id: 'RT-1',
          name: 'Suite familiar',
          max_adults: 2,
          max_children: 2,
          base_capacity: 4,
        },
        min_nightly_rate: 120,
        min_nightly_rate_label: '$120.00',
        total_estimated: 240,
        total_estimated_label: '$240.00',
      }],
      total: 11,
      page: 1,
      page_size: 10,
      total_pages: 2,
      has_prev: false,
      has_next: true,
      filters: {},
      alternative_destinations: [],
    };

    const page = mapHotelSearchResponse(dto, createHotelSearchFilters({ page: 1 }));
    const hotel = page.items[0];

    expect(page.pageSize).toBe(10);
    expect(page.hasNext).toBe(true);
    expect(hotel.name).toBe('Hotel Costa Azul');
    expect(hotel.destinationLabels).toEqual(['Madrid']);
    expect(hotel.generalAmenities).toEqual(['Wi-Fi', 'Piscina', 'Playa', 'Parking']);
    expect(hotel.minNightlyRate).toBe(120);
    expect(hotel.totalEstimated).toBe(240);
    expect(hotel.matchedRoomType?.name).toBe('Suite familiar');
  });

  it('uses operational display_name when hotel_name is absent', () => {
    const dto: HotelSearchDto = {
      items: [{
        prop_id: 7,
        display_name: 'Hotel Centro',
        destination_labels: [],
      }],
      total: 1,
      page: 1,
      page_size: 10,
      total_pages: 1,
      has_prev: false,
      has_next: false,
      filters: {},
      alternative_destinations: [],
    };

    const page = mapHotelSearchResponse(dto, createHotelSearchFilters());

    expect(page.items[0].name).toBe('Hotel Centro');
  });
});
