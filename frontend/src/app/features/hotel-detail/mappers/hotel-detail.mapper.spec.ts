import { mapHotelDetailResponse } from './hotel-detail.mapper';
import type { HotelDetailDto } from '../models/hotel-detail.dto';

/** DTO mínimo pero estructuralmente completo para el mapper. */
function makeDto(overrides: Partial<HotelDetailDto> = {}): HotelDetailDto {
  return {
    prop_id: 1,
    hotel_label: 'Hotel Lima Centro',
    country_display_name: 'Perú, Lima',
    prop_starrating: 4,
    review_label: '8.5',
    avg_price_label: 'S/ 120',
    min_rate_label: 'S/ 110',
    reservations: 10,
    clicks: 20,
    events: 3,
    promotions: 1,
    conversion_rate: 0.5,
    click_rate: 0.6,
    source_collection: 'test',
    top_destinations: [],
    top_visitor_countries: [],
    top_sites: [],
    hotel_rates: [],
    room_types: [],
    hotel_policies: null,
    hotel_images: [],
    hotel_content: null,
    review_count: 0,
    reviews: [],
    ...overrides,
  };
}

describe('mapHotelDetailResponse — galería de habitaciones', () => {
  it('arma una galería de varias fotos por habitación (real primero, placeholders después)', () => {
    const vm = mapHotelDetailResponse(
      makeDto({
        room_types: [
          {
            room_type_id: 'rt-1',
            name: 'Habitación Deluxe',
            base_capacity: 2,
            max_adults: 2,
            max_children: 1,
            is_active: true,
            image_url: 'https://cdn.example.com/deluxe.jpg',
          },
          {
            room_type_id: 'rt-2',
            name: 'Suite',
            base_capacity: 3,
            max_adults: 3,
            max_children: 2,
            is_active: true,
            image_url: '',
          },
        ],
      }),
    );

    // Con foto real: [real, placeholder, placeholder]
    expect(vm.roomTypes[0].images.length).toBe(3);
    expect(vm.roomTypes[0].images[0]).toBe('https://cdn.example.com/deluxe.jpg');
    expect(vm.roomTypes[0].images[1]).toMatch(/^https:\/\/loremflickr\.com\//);
    expect(vm.roomTypes[0].images[2]).toMatch(/^https:\/\/loremflickr\.com\//);

    // Sin foto real: placeholders deterministas (2), nunca vacío.
    expect(vm.roomTypes[1].images.length).toBe(2);
    expect(vm.roomTypes[1].images.every((u) => u.startsWith('https://loremflickr.com/'))).toBe(true);

    // Placeholders estables: mismo hotel + misma habitación → misma URL.
    const dto = makeDto({
      room_types: [
        {
          room_type_id: 'rt-2',
          name: 'Suite',
          base_capacity: 3,
          max_adults: 3,
          max_children: 2,
          is_active: true,
          image_url: '',
        },
      ],
    });
    const first = mapHotelDetailResponse(dto);
    const again = mapHotelDetailResponse(dto);
    expect(again.roomTypes[0].images).toEqual(first.roomTypes[0].images);

    // Habitaciones distintas no comparten fotos placeholder.
    const rt1 = vm.roomTypes[0].images.slice(1);
    const rt2 = vm.roomTypes[1].images;
    const intersection = rt1.filter((u) => rt2.includes(u));
    expect(intersection).toEqual([]);
  });
});
