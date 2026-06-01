import type {
  CreateRateCalendarRequestDto,
  CreateRatePlanRequestDto,
  RatesOptionsResponseDto,
  RatesSnapshotResponseDto
} from '../models/rates.dto';
import type { RatesPageViewModel } from '../models/rates.model';

export function mapRatesResponse(
  options: RatesOptionsResponseDto,
  snapshot: RatesSnapshotResponseDto
): RatesPageViewModel {
  return {
    property: {
      propId: snapshot.property.prop_id,
      hotelLabel: snapshot.property.hotel_label
    },
    options: {
      properties: options.property_options.map((item) => ({
        propId: item.prop_id,
        label: item.label
      })),
      ratePlans: options.rate_plan_options.map((item) => ({
        ratePlanId: item.rate_plan_id,
        name: item.name,
        baseRateLabel: item.base_rate_label,
        currency: item.currency
      }))
    },
    ratePlans: snapshot.rate_plans.map((item) => ({
      ratePlanId: item.rate_plan_id,
      name: item.name,
      description: item.description || 'Sin descripcion',
      baseRateLabel: item.base_rate_label,
      currency: item.currency,
      isActive: item.is_active
    })),
    calendar: snapshot.calendar.map((item) => ({
      date: item.date,
      ratePlanId: item.rate_plan_id,
      planName: item.plan_name,
      rateAmountLabel: item.rate_amount_label,
      minStayNights: item.min_stay_nights,
      isClosed: item.is_closed
    })),
    summary: {
      totalRatePlans: snapshot.summary.total_rate_plans,
      activeRatePlans: snapshot.summary.active_rate_plans,
      calendarRows: snapshot.summary.calendar_rows,
      closedDates: snapshot.summary.closed_dates
    }
  };
}

export function buildCreateRatePlanRequest(
  propId: number,
  value: {
    name: string;
    description: string;
    baseRate: number;
    currency: string;
    isActive: boolean;
  }
): CreateRatePlanRequestDto {
  return {
    prop_id: propId,
    name: value.name.trim(),
    description: value.description.trim(),
    base_rate: value.baseRate,
    currency: value.currency.trim().toUpperCase() || 'USD',
    is_active: value.isActive
  };
}

export function buildCreateRateCalendarRequest(
  propId: number,
  value: {
    ratePlanId: string;
    date: string;
    rateAmount: number;
    minStayNights: number;
    isClosed: boolean;
  }
): CreateRateCalendarRequestDto {
  return {
    prop_id: propId,
    rate_plan_id: value.ratePlanId,
    date: value.date,
    rate_amount: value.rateAmount,
    min_stay_nights: value.minStayNights,
    is_closed: value.isClosed
  };
}
