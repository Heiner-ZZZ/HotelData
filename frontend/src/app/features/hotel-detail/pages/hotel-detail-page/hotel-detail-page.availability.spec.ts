import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { HotelDetailPageComponent } from './hotel-detail-page';

describe('HotelDetailPageComponent — disponibilidad próximos 7 días (TDD)', () => {
  function setup() {
    TestBed.configureTestingModule({
      imports: [HotelDetailPageComponent],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    const fixture = TestBed.createComponent(HotelDetailPageComponent);
    fixture.detectChanges();
    const httpMock = TestBed.inject(HttpTestingController);
    // Flush initial hotel detail request (id 0 -> no request) and snapshot (id 0 -> no request) — no flush needed
    // But if hotelId is 0, no request; we need to set hotelId via route param
    // For this isolated unit test, we test the selection logic directly via component instance
    return { fixture, comp: fixture.componentInstance, httpMock };
  }

  it('selección de un día crea rango de 1 noche y persiste', () => {
    const { comp } = setup();
    // Simular snapshot para room RT1
    const mockSnapshot: any = {
      prop_id: 1,
      start_date: '2026-08-23',
      end_date: '2026-08-29',
      rooms: [
        {
          room_type_id: 'RT1',
          name: 'Habitacion Doble Premiun',
          is_active: true,
          base_capacity: 2,
          max_adults: 2,
          max_children: 0,
          availability: [
            { date: '2026-08-23', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
            { date: '2026-08-24', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
            { date: '2026-08-25', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
            { date: '2026-08-26', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
            { date: '2026-08-27', is_available: false, available_rooms: 0, min_rate: null, min_rate_label: null },
            { date: '2026-08-28', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
            { date: '2026-08-29', is_available: true, available_rooms: 1, min_rate: 135, min_rate_label: '$135.00' },
          ],
        },
      ],
    };
    // Inject snapshot directly via resource value (bypass http)
    (comp as any).roomAvailabilitySnapshot = (() => mockSnapshot) as any;
    // Mock localStorage and http
    const lsSpy = jest.spyOn(Storage.prototype, 'setItem');
    // First click on 2026-08-23
    comp.selectAvailabilityDay('RT1', mockSnapshot.rooms[0].availability[0] as any);
    expect(comp.selectedRanges()['RT1']).toEqual({ start: '2026-08-23', end: '2026-08-24' });
    expect(comp.selectedNights('RT1')).toBe(1);
    expect(comp.selectedTotal('RT1')).toBe('$135.00');
    expect(comp.isDayInRange('RT1', '2026-08-23')).toBe(true);
    expect(comp.isDayInRange('RT1', '2026-08-24')).toBe(false); // end exclusive
    // Second click on 2026-08-25 extends to 3 noches 23->26
    comp.selectAvailabilityDay('RT1', mockSnapshot.rooms[0].availability[2] as any);
    expect(comp.selectedRanges()['RT1']).toEqual({ start: '2026-08-23', end: '2026-08-26' });
    expect(comp.selectedNights('RT1')).toBe(3);
    expect(comp.selectedTotal('RT1')).toBe('$405.00');
    expect(comp.isDayInRange('RT1', '2026-08-24')).toBe(true);
    expect(comp.isDayInRange('RT1', '2026-08-25')).toBe(true);
    // Click on 2026-08-27 is not available -> should not change
    comp.selectAvailabilityDay('RT1', mockSnapshot.rooms[0].availability[4] as any);
    expect(comp.selectedRanges()['RT1']).toEqual({ start: '2026-08-23', end: '2026-08-26' });
    // Clicking 2026-08-28 which is after a gap (27 not available) should reset to single night on 28
    comp.selectAvailabilityDay('RT1', mockSnapshot.rooms[0].availability[5] as any);
    expect(comp.selectedRanges()['RT1']).toEqual({ start: '2026-08-28', end: '2026-08-29' });
    expect(comp.roomReserveQuery('RT1', 'Habitacion Doble Premiun')).toEqual({
      prop_id: comp['hotel']()?.id ?? undefined,
      room_type: 'RT1',
      room_type_name: 'Habitacion Doble Premiun',
      check_in: '2026-08-28',
      check_out: '2026-08-29',
    });
    lsSpy.mockRestore();
  });
});
