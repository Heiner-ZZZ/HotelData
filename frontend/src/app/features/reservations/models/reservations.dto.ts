export interface ReservationsListDto {
  items: ReservationListItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface ReservationListItemDto {
  booking_id: string;
  prop_id: number;
  status: string;
  booking_source: string;
  assigned_rooms?: string[];
  guest_name: string;
  guest_email: string;
  guest_phone?: string;
  cedula?: string;
  check_in_date: string;
  check_out_date: string;
  check_in_time?: string;
  check_out_time?: string;
  adults: number;
  children: number;
  rooms: number;
  created_at: string;
  total_price?: number | null;
  currency?: string;
  total_nights?: number;
  stay_status?: string;
  folio?: string;
  hotel?: ReservationHotelContextDto | null;
  check_in_time_actual?: string;
  check_out_time_actual?: string;
  check_in_by?: string;
  check_out_by?: string;
}

export interface ReservationHotelContextDto {
  prop_id: number;
  hotel_label: string;
  country: string | number | null;
  review_label: string;
  avg_price_label: string;
}

export interface ReservationOptionsDto {
  hotel_options: {
    prop_id: number;
    label: string;
  }[];
}

export interface ReservationCreateDto {
  booking_id: string;
  status: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  manual_reservation_id: string | null;
  hotel_label: string;
  hotel_prop_id: number;
  room_type_name: string | null;
  check_in_date: string;
  check_out_date: string;
  rooms: number;
  adults: number;
  children: number;
  guest_name: string;
  guest_email: string;
  discount_percent?: number | null;
  original_total_price?: number | null;
  transaction_id?: string;
  payment_method?: string;
  card_last4?: string;
  payment_status?: string;
  cancellation_policy?: string | null;
}

export interface ReservationPreviewDto {
  available: boolean;
  availability_message: string | null;
  total_price: number | null;
  currency: string;
  total_nights: number;
  tax_rate?: number;
  tax_amount?: number;
  tax_included?: boolean;
  cancellation_policy?: string | null;
  price_breakdown?: {
    base_nightly_rate: number | null;
    nights: number;
    base_total: number | null;
    included_amenities: { label: string; unit_price: number }[];
    selected_extras: { label: string; unit_price: number }[];
    amenity_total: number;
    rate_plan_name: string | null;
    subtotal: number | null;
    tax_amount: number;
    tax_rate: number;
    tax_included: boolean;
    total: number | null;
    grand_total: number | null;
  };
}

export interface NightBreakdownDto {
  date: string;
  rate: number;
  rooms: number;
  night_total: number;
}

export interface PriceBreakdownDto {
  nights: NightBreakdownDto[];
  subtotal: number;
  taxes: number;
  iva_rate: number;
  total: number;
  currency: string;
  source: string;
}

export interface RoomTypeInfoDto {
  room_type_id: string;
  name: string;
}

export interface ReservationDetailDto {
  booking: {
    booking_id: string;
    prop_id: number;
    status: string;
    booking_source: string;
    guest_name: string;
    guest_email: string;
    guest_phone: string;
    room_type_id: string;
    check_in_date: string;
    check_out_date: string;
    adults: number;
    children: number;
    rooms: number;
    comment: string;
    total_price: number | null;
    currency: string;
    total_nights: number;
    created_at: string;
    discount_percent?: number | null;
    original_total_price?: number | null;
    special_requests?: string[];
    stay_status?: string;
    transaction_id?: string;
    payment_method?: string;
    card_last4?: string;
    payment_status?: string;
    cancellation_free?: boolean;
    cancellation_penalty_percent?: number;
    cancellation_penalty_amount?: number;
  };
  guest: {
    guest_name: string;
    guest_email: string;
    guest_phone: string;
    cedula?: string | null;
  } | null;
  history: {
    status: string;
    changed_at: string;
    reason: string;
    changed_by: string;
  }[];
  manual: {
    manual_reservation_id: string;
  } | null;
  hotel: ReservationHotelContextDto | null;
  invoice: {
    id: string;
    invoice_number: string;
    subtotal: number;
    taxes: number;
    total: number;
    status: string;
    issued_at: string | null;
    paid_at: string | null;
  } | null;
  room_type: RoomTypeInfoDto | null;
  price_breakdown: PriceBreakdownDto | null;
  cancellation_policy: string | null;
  assigned_rooms?: {
    hotel_room_id: string;
    room_number: string;
    room_label: string;
    floor: string;
    room_status: string;
  }[];
  additional_charges?: {
    concept: string;
    amount: number;
    quantity: number;
    total: number;
    note: string;
    created_at: string;
  }[];
  amenities_count?: number;
  amenities_total?: number;
  can_cancel: boolean;
}

export interface ReservationCancelDto {
  booking_id: string;
  status: string;
}

export interface ReservationStatsDto {
  pending: number;
  confirmed: number;
  cancelled: number;
  rejected: number;
  checked_in: number;
  checked_out: number;
  total: number;
  active: number;
  completed: number;
  lost: number;
}

export interface ReservationConfirmRejectDto {
  booking_id: string;
  status: string;
}

/**
 * Raw backend response for the cancel-preview endpoint. Returned by
 * `ReservationsApiService.getCancelPreview()` and consumed by the
 * reservation-detail page's effect that drives the cancellation
 * confirmation dialog. `one_night_price` and `total_nights` are emitted
 * by the backend but weren't part of the inferred shape before; they
 * are typed as optional to match the runtime (`?? 0` / `?? 1` defaults).
 */
export interface CancelPreviewDto {
  booking_id: string;
  guest_name: string;
  check_in_date: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  free_cancellation: boolean;
  penalty_percent: number;
  penalty_amount: number;
  hours_until_checkin: number | null;
  cancellation_hours: number;
  one_night_price?: number;
}
