export interface RatesPropertyOptionDto {
  prop_id: number;
  label: string;
}

export interface RatePlanOptionDto {
  rate_plan_id: string;
  name: string;
  base_rate_label: string;
  currency: string;
}

export interface RatesOptionsResponseDto {
  property_options: RatesPropertyOptionDto[];
  selected_prop_id: number | null;
  rate_plan_options: RatePlanOptionDto[];
}

export interface RatePlanDto {
  rate_plan_id: string;
  name: string;
  description: string;
  base_rate: number | null;
  base_rate_label: string;
  currency: string;
  is_active: boolean;
}

export interface RateCalendarRowDto {
  date: string;
  rate_plan_id: string;
  plan_name: string;
  rate_amount: number | null;
  rate_amount_label: string;
  min_stay_nights: number | null;
  is_closed: boolean;
}

export interface RatesSnapshotResponseDto {
  property: {
    prop_id: number;
    hotel_label: string;
  };
  rate_plans: RatePlanDto[];
  calendar: RateCalendarRowDto[];
  summary: {
    total_rate_plans: number;
    active_rate_plans: number;
    calendar_rows: number;
    closed_dates: number;
  };
}

export interface CreateRatePlanRequestDto {
  prop_id: number;
  name: string;
  description: string;
  base_rate: number;
  currency: string;
  is_active: boolean;
}

export interface CreateRateCalendarRequestDto {
  prop_id: number;
  rate_plan_id: string;
  date: string;
  rate_amount: number;
  min_stay_nights: number;
  is_closed: boolean;
}
