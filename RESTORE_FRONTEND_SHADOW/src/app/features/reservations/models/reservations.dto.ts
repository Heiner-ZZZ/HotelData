export interface ReservationHotelOptionDto {
  prop_id: number;
  label: string;
}

export interface ReservationHotelContextDto {
  prop_id: number;
  hotel_label: string;
  country: string | number | null;
  review_label: string;
  avg_price_label: string;
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
  comment: string;
  created_at: string;
  hotel?: ReservationHotelContextDto | null;
}

export interface ReservationListResponseDto {
  items: ReservationListItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface ReservationOptionsResponseDto {
  hotel: ReservationHotelContextDto | null;
  hotel_options: ReservationHotelOptionDto[];
  form_values: {
    prop_id: number | '';
    guest_name: string;
    guest_email: string;
    check_in_date: string;
    check_out_date: string;
    adults: number;
    children: number;
    rooms: number;
    comment: string;
  };
}

export interface ReservationCreateResponseDto {
  booking_id: string;
  status: string;
  manual_reservation_id: string | null;
}

export interface ReservationHistoryItemDto {
  status: string;
  changed_at: string;
  reason: string;
  changed_by: string;
}

export interface ReservationDetailResponseDto {
  booking: ReservationListItemDto;
  guest: {
    guest_name: string;
    guest_email: string;
  } | null;
  history: ReservationHistoryItemDto[];
  manual: {
    manual_reservation_id: string;
  } | null;
  hotel: ReservationHotelContextDto | null;
  can_cancel: boolean;
}
