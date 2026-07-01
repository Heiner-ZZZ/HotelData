export interface RatesDto {
  prop_id: number;
  hotel_label: string;
  manual_override?: boolean;
  profile_badge?: string;
  room_types: Array<{
    room_type_id: string;
    name: string;
  }>;
  rate_plans: Array<{
    rate_plan_id: string;
    prop_id: number;
    name: string;
    description: string;
    base_rate: number;
    base_rate_label: string;
    currency: string;
    room_type_id?: string;
    is_active: boolean;
    eligible_roles?: string[];
    updated_at_label?: string;
  }>;
  calendar: Array<{
    date: string;
    rate_plan_id: string;
    plan_name: string;
    rate_amount: number;
    rate_amount_label: string;
    min_stay_nights: number;
    is_closed: boolean;
  }>;
  rate_rules?: Array<{
    rule_id?: string;
    rule_name?: string;
    rate_plan_id?: string;
    name?: string;
    description?: string;
    start_date?: string;
    end_date?: string;
    price_override?: number;
    range_label?: string;
  }>;
  promotions?: Array<{
    campaign_id: string;
    name: string;
    description?: string;
    discount_percent?: number;
    start_date?: string;
    end_date?: string;
    is_active: boolean;
  }>;
  coupon_codes?: Array<{
    coupon_code: string;
    campaign_id: string;
    is_active: boolean;
  }>;
}

export interface RatesOptionsDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
  total?: number;
  page?: number;
  page_size?: number;
  has_next?: boolean;
  rate_plans?: Array<{
    rate_plan_id: string;
    name: string;
  }>;
}
