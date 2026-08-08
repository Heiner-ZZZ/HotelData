import type { PoliciesDto, PoliciesOptionsDto, PoliciesSaveDto } from '../models/policies.dto';
import type { PoliciesViewModel, PolicyPropertyOption, PropertyOptionsPage } from '../models/policies.model';

export function mapPolicies(dto: PoliciesDto): PoliciesViewModel {
  const checkIn = dto.policies.check_in_time || 'Pendiente';
  const checkOut = dto.policies.check_out_time || 'Pendiente';
  const cancellation = dto.policies.cancellation_policy || 'Sin politica registrada';
  const cancelHours = dto.policies.cancellation_hours ?? 0;
  const cancelPenaltyPct = dto.policies.cancellation_penalty_percent ?? 100;
  const minStay = dto.policies.min_stay ?? 0;
  const maxStay = dto.policies.max_stay ?? 0;
  return {
    propId: dto.hotel.prop_id,
    hotelName: dto.hotel.display_name,
    countryLabel: dto.hotel.country_display_name,
    reviewLabel: dto.hotel.review_score_label,
    avgPriceLabel: dto.performance.avg_price_label,
    sourceCollection: dto.performance.source_collection,
    checkInTime: dto.policies.check_in_time || '',
    checkOutTime: dto.policies.check_out_time || '',
    cancellationPolicy: dto.policies.cancellation_policy || '',
    petPolicy: dto.policies.pet_policy || '',
    childrenPolicy: dto.policies.children_policy || '',
    extraBedPolicy: dto.policies.extra_bed_policy || '',
    paymentPolicy: dto.policies.payment_policy || '',
    houseRules: dto.policies.house_rules || '',
    roomTypeId: dto.policies.room_type_id || '',
    ratePlanId: dto.policies.rate_plan_id || '',
    cancellationHours: cancelHours,
    cancellationPenaltyPercent: cancelPenaltyPct,
    petsAllowed: dto.policies.pets_allowed ?? false,
    petFee: dto.policies.pet_fee ?? 0,
    childrenAllowed: dto.policies.children_allowed ?? false,
    extraBedFee: dto.policies.extra_bed_fee ?? 0,
    minStay: minStay,
    maxStay: maxStay,
    roomTypes: (dto.room_types ?? []).map(r => ({
      id: r.room_type_id,
      name: r.name
    })),
    ratePlanOptions: (dto.rate_plan_options ?? []).map(rp => ({
      id: rp.rate_plan_id,
      name: rp.name,
    })),
    summary: [
      { label: 'Check-in', value: checkIn, detail: 'Horario de llegada' },
      { label: 'Check-out', value: checkOut, detail: 'Horario de salida' },
      { label: 'Cancelacion', value: cancelHours > 0 ? `${cancelHours}h antes` : cancellation, detail: 'Politica comercial' },
      { label: 'Estancia', value: minStay > 0 ? `${minStay}-${maxStay || '∞'} noches` : 'Flexible', detail: 'Min/Max estancia' },
      { label: 'Mascotas', value: dto.policies.pets_allowed ? 'Sí' : 'No', detail: dto.policies.pet_fee ? `$${dto.policies.pet_fee} cargo` : 'Sin cargo' }
    ]
  };
}

export function mapPoliciesOptions(dto: PoliciesOptionsDto): PolicyPropertyOption[] | PropertyOptionsPage {
  const items = dto.properties.map((item) => ({
    propId: item.prop_id,
    label: item.display_name || `Hotel ${item.prop_id}`
  }));
  if (dto.total !== undefined && dto.has_next !== undefined) {
    return {
      items,
      total: dto.total,
      page: dto.page ?? 1,
      pageSize: dto.page_size ?? items.length,
      hasNext: dto.has_next
    };
  }
  return items;
}

export function mapPoliciesPayload(vm: PoliciesViewModel): PoliciesSaveDto {
  return {
    prop_id: vm.propId,
    check_in_time: vm.checkInTime,
    check_out_time: vm.checkOutTime,
    cancellation_policy: vm.cancellationPolicy,
    pet_policy: vm.petPolicy,
    children_policy: vm.childrenPolicy,
    extra_bed_policy: vm.extraBedPolicy,
    payment_policy: vm.paymentPolicy,
    house_rules: vm.houseRules,
    room_type_id: vm.roomTypeId || undefined,
    rate_plan_id: vm.ratePlanId || undefined,
    // Always send numeric/boolean fields; backend handles via default=None
    cancellation_hours: vm.cancellationHours,
    cancellation_penalty_percent: vm.cancellationPenaltyPercent,
    pets_allowed: vm.petsAllowed,
    pet_fee: vm.petFee,
    children_allowed: vm.childrenAllowed,
    extra_bed_fee: vm.extraBedFee,
    min_stay: vm.minStay,
    max_stay: vm.maxStay
  };
}
