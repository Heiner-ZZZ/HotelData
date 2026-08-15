export interface PolicyRoomTypeItem {
  room_type_id: string;
  name: string;
}

export interface PoliciesDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    review_score_label: string;
  };
  performance: {
    avg_price_label: string;
    source_collection: string;
  };
  policies: {
    check_in_time: string;
    check_out_time: string;
    early_check_in_enabled?: boolean;
    early_check_in_courtesy_minutes?: number;
    early_check_in_default_fee?: number;
    late_checkout_enabled?: boolean;
    late_checkout_courtesy_minutes?: number;
    late_checkout_default_fee?: number;
    guaranteed_reservation?: boolean;
    late_arrival_cutoff?: string;
    no_show_execution?: 'next_day' | 'same_day_cutoff' | 'manual';
    cancellation_policy: string;
    pet_policy: string;
    children_policy: string;
    extra_bed_policy?: string;
    payment_policy?: string;
    house_rules?: string;
    room_type_id?: string;
    rate_plan_id?: string;
    // SPEC 022 structured fields
    cancellation_hours?: number;
    cancellation_penalty_percent?: number;
    pets_allowed?: boolean;
    pet_fee?: number;
    children_allowed?: boolean;
    extra_bed_fee?: number;
    min_stay?: number;
    max_stay?: number;
  };
  room_types?: PolicyRoomTypeItem[];
  per_room_policies?: Record<string, unknown>[];
  rate_plan_options?: { rate_plan_id: string; name: string }[];
}

export interface PoliciesOptionsDto {
  properties: {
    prop_id: number;
    display_name: string;
  }[];
  total?: number;
  page?: number;
  page_size?: number;
  has_next?: boolean;
}

export interface PoliciesSaveDto {
  prop_id: number;
  check_in_time: string;
  check_out_time: string;
  early_check_in_enabled?: boolean;
  early_check_in_courtesy_minutes?: number;
  early_check_in_default_fee?: number;
  late_checkout_enabled?: boolean;
  late_checkout_courtesy_minutes?: number;
  late_checkout_default_fee?: number;
  guaranteed_reservation?: boolean;
  late_arrival_cutoff?: string;
  no_show_execution?: 'next_day' | 'same_day_cutoff' | 'manual';
  cancellation_policy: string;
  pet_policy: string;
  children_policy: string;
  extra_bed_policy: string;
  payment_policy: string;
  house_rules: string;
  room_type_id?: string;
  rate_plan_id?: string;
  // SPEC 022 structured fields
  cancellation_hours?: number;
  cancellation_penalty_percent?: number;
  pets_allowed?: boolean;
  pet_fee?: number;
  children_allowed?: boolean;
  extra_bed_fee?: number;
  min_stay?: number;
  max_stay?: number;
}
