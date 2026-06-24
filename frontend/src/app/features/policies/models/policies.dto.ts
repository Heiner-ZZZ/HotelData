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
  };
  room_types?: PolicyRoomTypeItem[];
  per_room_policies?: Array<Record<string, unknown>>;
}

export interface PoliciesOptionsDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
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
}
