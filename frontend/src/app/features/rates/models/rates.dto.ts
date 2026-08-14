export interface RatesDto {
  prop_id: number;
  hotel_label: string;
  manual_override?: boolean;
  profile_badge?: string;
  /** Tarifa base mínima configurable (system_config.min_base_rate) — la usa
   *  el form de Tarifas para validar antes de enviar. Default $10. */
  min_base_rate?: number;
  room_types: {
    room_type_id: string;
    name: string;
  }[];
  rate_plans: {
    rate_plan_id: string;
    prop_id: number;
    name: string;
    description: string;
    base_rate: number;
    base_rate_label: string;
    currency: string;
    room_type_id?: string;
    applicable_room_types?: string[];
    is_active: boolean;
    eligible_roles?: string[];
    included_amenities?: string[];
    updated_at_label?: string;
  }[];
  calendar: {
    date: string;
    rate_plan_id: string;
    plan_name: string;
    rate_amount: number;
    rate_amount_label: string;
    min_stay_nights: number;
    is_closed: boolean;
    /** 'generated' = creada por Generar calendario (bulk); ausente = editada a mano. */
    source?: string;
  }[];
  rate_rules?: {
    rule_id?: string;
    rule_name?: string;
    rate_plan_id?: string;
    name?: string;
    description?: string;
    start_date?: string;
    end_date?: string;
    price_override?: number;
    range_label?: string;
  }[];
  promotions?: {
    campaign_id: string;
    name: string;
    description?: string;
    discount_percent?: number;
    start_date?: string;
    end_date?: string;
    is_active: boolean;
  }[];
  coupon_codes?: {
    coupon_code: string;
    campaign_id: string;
    is_active: boolean;
  }[];
  /** Hueco tarifas-vs-inventario: noches disponibles sin tarifa abierta
   *  (no vendibles en el search). null cuando no hay hueco accionable. */
  rate_coverage?: {
    rate_last_date: string | null;
    inventory_last_date: string;
    gap_nights: number;
    gap_start: string;
    gap_end: string;
  } | null;
}

export interface RatesOptionsDto {
  properties: {
    prop_id: number;
    display_name: string;
  }[];
  total?: number;
  page?: number;
  page_size?: number;
  has_next?: boolean;
  rate_plans?: {
    rate_plan_id: string;
    name: string;
  }[];
}
