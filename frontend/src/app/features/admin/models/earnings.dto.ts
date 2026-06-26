export interface EarningsSummaryDto {
  total_commission: number;
  total_bookings: number;
  avg_commission: number;
  pending_count: number;
  paid_count: number;
}

export interface EarningsItemDto {
  booking_id: string;
  prop_id: number;
  hotel_name: string;
  commission_pct: number;
  booking_total: number;
  commission_amount: number;
  status: string;
  created_at: string;
}

export interface EarningsListDto {
  items: EarningsItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface WeeklyEarningPointDto {
  label: string;
  total_commission: number;
  total_bookings: number;
  paid_count: number;
  pending_count: number;
}
