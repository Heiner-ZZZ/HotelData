export interface RatesDto {
  prop_id: number;
  hotel_label: string;
  rate_plans: Array<{
    rate_plan_id: string;
    prop_id: number;
    name: string;
    description: string;
    base_rate: number;
    base_rate_label: string;
    currency: string;
    is_active: boolean;
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
}

export interface RatesOptionsDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
  rate_plans?: Array<{
    rate_plan_id: string;
    name: string;
  }>;
}
