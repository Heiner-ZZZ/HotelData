import type { RatesDto, RatesOptionsDto } from '../models/rates.dto';
import type { RatePlanOption, RatePropertyOption, RatesViewModel } from '../models/rates.model';

export function mapRatesResponse(dto: RatesDto): RatesViewModel {
  return {
    propId: dto.prop_id,
    hotelLabel: dto.hotel_label,
    manualOverride: dto.manual_override ?? false,
    profileBadge: dto.profile_badge || (dto.manual_override ? 'Nombre editado manualmente' : 'Nombre generado'),
    ratePlans: dto.rate_plans.map((plan) => ({
      id: plan.rate_plan_id,
      name: plan.name,
      description: plan.description || 'Sin descripción',
      baseRateLabel: plan.base_rate_label,
      currency: plan.currency,
      activeLabel: plan.is_active ? 'Sí' : 'No'
    })),
    calendar: dto.calendar.map((item) => ({
      date: item.date,
      planName: item.plan_name,
      rateAmountLabel: item.rate_amount_label,
      minStayNights: item.min_stay_nights,
      closedLabel: item.is_closed ? 'Sí' : 'No'
    })),
    rateRules: (dto.rate_rules || []).map((rule) => ({
      label: rule.rule_name || rule.rate_plan_id || 'Regla operativa',
      detail: rule.description || 'Sin detalle'
    })),
    promotions: (dto.promotions || []).map((promo) => ({
      name: promo.name || promo.campaign_id,
      activeLabel: promo.is_active ? 'Sí' : 'No'
    })),
    coupons: (dto.coupon_codes || []).map((coupon) => ({
      code: coupon.coupon_code,
      activeLabel: coupon.is_active ? 'Sí' : 'No'
    }))
  };
}

export function mapRatesPropertyOptions(dto: RatesOptionsDto): RatePropertyOption[] {
  return dto.properties.map((item) => ({
    propId: item.prop_id,
    label: item.display_name || `Hotel ${item.prop_id}`
  }));
}

export function mapRatePlanOptions(dto: RatesOptionsDto): RatePlanOption[] {
  return (dto.rate_plans || []).map((item) => ({
    id: item.rate_plan_id,
    label: `${item.name} · ${item.rate_plan_id}`
  }));
}
