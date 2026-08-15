import { mapPolicies, mapPoliciesPayload } from './policies.mapper';
import type { PoliciesDto } from '../models/policies.dto';
import type { PoliciesViewModel } from '../models/policies.model';

const DTO: PoliciesDto = {
  hotel: {
    prop_id: 42,
    display_name: 'Hotel Test',
    country_display_name: 'Perú',
    review_score_label: '8.2',
  },
  performance: { avg_price_label: '120', source_collection: 'test' },
  policies: {
    check_in_time: '15:00',
    check_out_time: '12:00',
    cancellation_policy: '',
    pet_policy: '',
    children_policy: '',
  },
};

describe('mapPolicies (wire → model)', () => {
  it('usa defaults de política late-arrival y late-checkout cuando el backend no envía los campos', () => {
    const vm = mapPolicies(DTO);
    expect(vm.guaranteedReservation).toBe(false);
    expect(vm.lateArrivalCutoff).toBe('23:59');
    expect(vm.noShowExecution).toBe('next_day');
    expect(vm.lateCheckoutEnabled).toBe(true);
    expect(vm.lateCheckoutCourtesyMinutes).toBe(60);
    expect(vm.lateCheckoutDefaultFee).toBe(0);
  });

  it('mapea los campos late-checkout cuando vienen del backend', () => {
    const vm = mapPolicies({
      ...DTO,
      policies: {
        ...DTO.policies,
        late_checkout_enabled: false,
        late_checkout_courtesy_minutes: 120,
        late_checkout_default_fee: 25,
      },
    });
    expect(vm.lateCheckoutEnabled).toBe(false);
    expect(vm.lateCheckoutCourtesyMinutes).toBe(120);
    expect(vm.lateCheckoutDefaultFee).toBe(25);
  });

  it('mapea los campos late-arrival cuando vienen del backend', () => {
    const vm = mapPolicies({
      ...DTO,
      policies: {
        ...DTO.policies,
        guaranteed_reservation: true,
        late_arrival_cutoff: '02:30',
        no_show_execution: 'manual',
      },
    });
    expect(vm.guaranteedReservation).toBe(true);
    expect(vm.lateArrivalCutoff).toBe('02:30');
    expect(vm.noShowExecution).toBe('manual');
  });
});

describe('mapPoliciesPayload (model → wire)', () => {
  function vm(overrides: Partial<PoliciesViewModel> = {}): PoliciesViewModel {
    return {
      propId: 42,
      hotelName: 'Hotel Test',
      countryLabel: 'Perú',
      reviewLabel: '8.2',
      avgPriceLabel: '120',
      sourceCollection: 'test',
      checkInTime: '15:00',
      checkOutTime: '12:00',
      earlyCheckInEnabled: true,
      earlyCheckInCourtesyMinutes: 60,
      earlyCheckInDefaultFee: 0,
      lateCheckoutEnabled: true,
      lateCheckoutCourtesyMinutes: 60,
      lateCheckoutDefaultFee: 0,
      guaranteedReservation: false,
      lateArrivalCutoff: '23:59',
      noShowExecution: 'next_day',
      cancellationPolicy: '',
      petPolicy: '',
      childrenPolicy: '',
      extraBedPolicy: '',
      paymentPolicy: '',
      houseRules: '',
      roomTypeId: '',
      ratePlanId: '',
      cancellationHours: 0,
      cancellationPenaltyPercent: 100,
      petsAllowed: false,
      petFee: 0,
      childrenAllowed: false,
      extraBedFee: 0,
      minStay: 0,
      maxStay: 0,
      roomTypes: [],
      ratePlanOptions: [],
      summary: [],
      ...overrides,
    };
  }

  it('envía los campos late-arrival en el payload de guardado', () => {
    const payload = mapPoliciesPayload(
      vm({ guaranteedReservation: true, lateArrivalCutoff: '02:30', noShowExecution: 'manual' }),
    );
    expect(payload.guaranteed_reservation).toBe(true);
    expect(payload.late_arrival_cutoff).toBe('02:30');
    expect(payload.no_show_execution).toBe('manual');
  });

  it('envía los campos late-checkout en el payload de guardado', () => {
    const payload = mapPoliciesPayload(
      vm({ lateCheckoutEnabled: false, lateCheckoutCourtesyMinutes: 90, lateCheckoutDefaultFee: 20 }),
    );
    expect(payload.late_checkout_enabled).toBe(false);
    expect(payload.late_checkout_courtesy_minutes).toBe(90);
    expect(payload.late_checkout_default_fee).toBe(20);
  });
});
