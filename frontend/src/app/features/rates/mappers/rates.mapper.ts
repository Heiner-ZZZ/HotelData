import type { RatesDto, RatesOptionsDto } from '../models/rates.dto';
import type { PropertyOptionsPage, RatePlanOption, RatePropertyOption, RatesViewModel } from '../models/rates.model';

export function mapRatesResponse(dto: RatesDto): RatesViewModel {
  return {
    propId: dto.prop_id,
    hotelLabel: dto.hotel_label,
    manualOverride: dto.manual_override ?? false,
    profileBadge: dto.profile_badge || (dto.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    minBaseRate: dto.min_base_rate ?? 10,
    roomTypes: (dto.room_types || []).map((rt) => ({
      id: rt.room_type_id,
      name: rt.name
    })),
    ratePlans: dto.rate_plans.map((plan) => ({
      id: plan.rate_plan_id,
      name: plan.name,
      description: plan.description || 'Sin descripción',
      baseRateLabel: plan.base_rate_label,
      baseRate: plan.base_rate,
      currency: plan.currency,
      roomTypeId: plan.room_type_id,
      applicableRoomTypes: plan.applicable_room_types ?? (plan.room_type_id ? [plan.room_type_id] : []),
      activeLabel: plan.is_active ? 'Sí' : 'No',
      eligibleRoles: plan.eligible_roles ?? [],
      includedAmenities: plan.included_amenities ?? []
    })),
    calendar: dto.calendar.map((item) => ({
      date: item.date,
      ratePlanId: item.rate_plan_id,
      planName: item.plan_name,
      rateAmount: item.rate_amount,
      rateAmountLabel: item.rate_amount_label,
      minStayNights: item.min_stay_nights,
      isClosed: item.is_closed,
      closedLabel: item.is_closed ? 'Sí' : 'No',
      source: item.source ?? ''
    })),
    rateRules: (dto.rate_rules || []).map((rule) => ({
      label: rule.rule_name || rule.rate_plan_id || 'Regla operativa',
      detail: rule.description || 'Sin detalle'
    })),
    seasonalRules: (dto.rate_rules || [])
      .filter((rule) => rule.start_date)
      .map((rule) => ({
        ruleId: rule.rule_id || '',
        name: rule.name || '',
        ratePlanId: rule.rate_plan_id || '',
        startDate: rule.start_date || '',
        endDate: rule.end_date || '',
        priceOverride: rule.price_override ?? 0,
        rangeLabel: rule.range_label || `${rule.start_date} -> ${rule.end_date}`
      })),
    promotions: (dto.promotions || []).map((promo) => ({
      campaignId: promo.campaign_id,
      name: promo.name || promo.campaign_id,
      description: promo.description || '',
      discountPercent: promo.discount_percent ?? 0,
      dateRange: [promo.start_date, promo.end_date].filter(Boolean).join(' → ') || '',
      activeLabel: promo.is_active ? 'Sí' : 'No'
    })),
    coupons: (dto.coupon_codes || []).map((coupon) => ({
      code: coupon.coupon_code,
      activeLabel: coupon.is_active ? 'Sí' : 'No',
      campaignId: coupon.campaign_id || ''
    })),
    rateCoverage: dto.rate_coverage
      ? {
          rateLastDate: dto.rate_coverage.rate_last_date,
          inventoryLastDate: dto.rate_coverage.inventory_last_date,
          gapNights: dto.rate_coverage.gap_nights,
          gapStart: dto.rate_coverage.gap_start,
          gapEnd: dto.rate_coverage.gap_end,
        }
      : null
  };
}

export function mapRatesPropertyOptions(dto: RatesOptionsDto): RatePropertyOption[] | PropertyOptionsPage {
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

export function mapRatePlanOptions(dto: RatesOptionsDto): RatePlanOption[] {
  return (dto.rate_plans || []).map((item) => ({
    id: item.rate_plan_id,
    label: `${item.name} · ${item.rate_plan_id}`
  }));
}
