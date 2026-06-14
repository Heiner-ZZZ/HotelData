import type { PoliciesDto, PoliciesOptionsDto, PoliciesSaveDto } from '../models/policies.dto';
import type { PoliciesViewModel, PolicyPropertyOption, PropertyOptionsPage } from '../models/policies.model';

export function mapPolicies(dto: PoliciesDto): PoliciesViewModel {
  const checkIn = dto.policies.check_in_time || 'Pendiente';
  const checkOut = dto.policies.check_out_time || 'Pendiente';
  const cancellation = dto.policies.cancellation_policy || 'Sin politica registrada';
  const payments = dto.policies.payment_policy || 'Sin politica de pagos';
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
    summary: [
      { label: 'Check-in', value: checkIn, detail: 'Horario de llegada' },
      { label: 'Check-out', value: checkOut, detail: 'Horario de salida' },
      { label: 'Cancelacion', value: cancellation, detail: 'Politica comercial' },
      { label: 'Pagos', value: payments, detail: 'Cobros y garantias' }
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
    house_rules: vm.houseRules
  };
}
