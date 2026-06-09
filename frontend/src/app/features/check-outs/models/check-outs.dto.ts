export interface CheckOutsDto {
  operation_date: string;
  prop_id: number | null;
  property_options: Array<{ prop_id: number; label: string }>;
  summary: {
    departures_today: number;
    pending: number;
    completed: number;
    cancelled_or_no_show: number;
  };
  items: Array<{
    booking_id: string;
    prop_id: number;
    hotel_label: string;
    guest_name: string;
    guest_email: string;
    date: string;
    reservation_status_label: string;
    stay_status_label: string;
    rooms_label: string;
    estimated_time: string;
    notes: string;
    balance_label: string;
    can_complete: boolean;
  }>;
}
