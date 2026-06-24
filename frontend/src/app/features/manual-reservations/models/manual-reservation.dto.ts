export interface ManualReservationListItemDto {
  booking_id: string;
  prop_id: number;
  hotel: { hotel_label: string } | null;
  guest_name: string;
  guest_email: string;
  status: string;
  check_in_date: string;
  check_out_date: string;
  adults: number;
  children: number;
  rooms: number;
  total_price: number | null;
  currency: string;
  total_nights: number;
  created_at: string;
  created_by: string;
}

export interface ManualReservationCreateDto {
  prop_id: number;
  room_type_id: string;
  guest_name: string;
  guest_email: string;
  guest_phone?: string;
  check_in_date: string;
  check_out_date: string;
  adults: number;
  children: number;
  rooms: number;
  comment?: string;
}

export interface ManualReservationResultDto {
  booking_id: string;
  status: string;
  total_price: number | null;
  currency: string;
  total_nights: number;
  manual_reservation_id: string | null;
}

export interface ManualReservationOptionDto {
  prop_id: number;
  display_name: string;
}

export interface ManualReservationRoomTypeDto {
  room_type_id: string;
  name: string;
  max_adults: number;
  max_children: number;
  base_capacity: number;
}
