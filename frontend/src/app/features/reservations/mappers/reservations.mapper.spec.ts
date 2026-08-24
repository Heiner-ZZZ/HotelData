import { mapReservationDetail } from './reservations.mapper';

describe('mapReservationDetail — no-show (fuente de verdad del importe)', () => {
  it('mapea penalización, porcentaje y folio desde el wire plano', () => {
    const vm = mapReservationDetail({
      booking_id: 'BK-1',
      status: 'confirmed',
      stay_status: 'no_show',
      no_show_penalty_amount: 47.94,
      no_show_penalty_percent: 51,
      no_show_folio_number: 'FL-NS-1',
      total_price: 188,
      currency: 'USD',
      total_nights: 2,
      rooms: 1,
      check_in_date: '2026-08-20',
      check_out_date: '2026-08-22',
      booking_source: 'web',
      guest_name: 'No Show Guest',
      guest_email: 'noshow@test.com',
      guest_phone: '',
      created_at: '2026-08-07T20:26:28Z',
      history: [],
      assigned_rooms: [],
      additional_charges: [],
    } as Parameters<typeof mapReservationDetail>[0]);

    expect(vm.stayStatus).toBe('no_show');
    expect(vm.noShowPenaltyAmount).toBe(47.94);
    expect(vm.noShowPenaltyPercent).toBe(51);
    expect(vm.noShowFolioNumber).toBe('FL-NS-1');
  });
});
