export interface CheckInsDto {
  operation_date: string;
  prop_id: number | null;
  property_options: { prop_id: number; label: string }[];
  summary: {
    arrivals_today: number;
    pending: number;
    completed: number;
    cancelled_or_no_show: number;
  };
  items: {
    booking_id: string;
    prop_id: number;
    hotel_label: string;
    guest_name: string;
    guest_email: string;
    date: string;
    check_in_date: string;
    check_in_time: string;
    check_out_date: string;
    reservation_status_label: string;
    stay_status_label: string;
    rooms_label: string;
    assigned_rooms: string[];
    assigned_room_numbers: string[];
    room_numbers_label: string[];
    estimated_time: string;
    estimated_arrival_time: string;
    late_checkin: boolean;
    notes: string;
    can_complete: boolean;
  }[];
}
