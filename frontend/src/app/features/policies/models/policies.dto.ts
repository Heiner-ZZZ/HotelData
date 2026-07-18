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
    cancellation_policy: string;
    pet_policy: string;
    children_policy: string;
    extra_bed_policy?: string;
    payment_policy?: string;
    house_rules?: string;
    room_type_id?: string;
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
  cancellation_policy: string;
  pet_policy: string;
  children_policy: string;
  extra_bed_policy: string;
  payment_policy: string;
  house_rules: string;
  room_type_id?: string;
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
