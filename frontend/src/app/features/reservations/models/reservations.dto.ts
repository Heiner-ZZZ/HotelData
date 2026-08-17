export interface ReservationsListDto {
  items: ReservationListItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

/**
 * Per-room snapshot returned by `GET /api/reservations` (list + detail)
 * post-FK-migration. Mirrors backend `AssignedRoomSnapshot` in
 * `server/src/app/modules/reservations/schemas.py` (Option B schema).
 * All optional fields tolerate pre-migration Mongo rows that stored
 * only `hotel_room_id`.
 */
export interface AssignedRoomSnapshotDto {
  hotel_room_id: string;
  room_number?: string | null;
  room_label?: string | null;
  floor?: string | null;
  room_status?: string | null;
}

export interface ReservationListItemDto {
  booking_id: string;
  prop_id: number;
  status: string;
  booking_source: string;
  assigned_rooms?: AssignedRoomSnapshotDto[];
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
  /** Ventana de reapertura de no-show (server-authoritative): 'open' | 'too_late' | 'stay_ended' | null. */
  reopen_window?: string | null;
  /** Marca de reapertura: el gerente reabrió el no-show porque el huésped llegó tras el no-show. */
  no_show_reopened_at?: string | null;
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
  deposit_required?: boolean;
  deposit_percent?: number;
  min_deposit_amount?: number;
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
  special_request_fulfillment?: { label: string; status: string; fulfilled_at?: string | null }[];
  amenity_fulfillment?: { label: string; status: string; fulfilled_at?: string | null }[];
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
    selected_amenities?: string[];
    stay_status?: string;
    /** Server-stamped late check-out outcome; never inferred by the client. */
    check_out_mode?: 'normal' | 'late_courtesy' | 'late_approved' | string | null;
    late_checkout_minutes?: number | null;
    late_checkout_policy_time?: string | null;
    check_out_date_actual?: string | null;
    check_out_time_actual?: string | null;
    estimated_arrival_time?: string;
    late_checkin?: boolean;
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
  assigned_rooms?: AssignedRoomSnapshotDto[];
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
  /** Depósito real registrado al confirmar (billing, shift-gated). */
  deposit?: {
    amount: number;
    method: string;
    reference?: string;
    status: string;
    paid_at?: string | null;
  } | null;
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
