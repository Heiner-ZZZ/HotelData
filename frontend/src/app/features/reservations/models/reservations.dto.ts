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
  guest_name: string;
  guest_email: string;
  check_in_date: string;
  check_out_date: string;
  adults: number;
  children: number;
  rooms: number;
  created_at: string;
  hotel?: ReservationHotelContextDto | null;
}

export interface ReservationHotelContextDto {
  prop_id: number;
  hotel_label: string;
  country: string | number | null;
  review_label: string;
  avg_price_label: string;
}

export interface ReservationOptionsDto {
  hotel_options: Array<{
    prop_id: number;
    label: string;
  }>;
}

export interface ReservationCreateDto {
  booking_id: string;
  status: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  manual_reservation_id: string | null;
}

export interface ReservationPreviewDto {
  available: boolean;
  availability_message: string | null;
  total_price: number | null;
  currency: string;
  total_nights: number;
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
  };
  guest: {
    guest_name: string;
    guest_email: string;
    guest_phone: string;
  } | null;
  history: Array<{
    status: string;
    changed_at: string;
    reason: string;
    changed_by: string;
  }>;
  manual: {
    manual_reservation_id: string;
  } | null;
  hotel: ReservationHotelContextDto | null;
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
