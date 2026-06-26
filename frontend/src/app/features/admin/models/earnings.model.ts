export interface EarningsSummary {
  totalCommission: number;
  totalBookings: number;
  avgCommission: number;
  pendingCount: number;
  paidCount: number;
}

export interface EarningsItem {
  bookingId: string;
  propId: number;
  hotelName: string;
  commissionPct: number;
  bookingTotal: number;
  commissionAmount: number;
  status: string;
  createdAt: string;
}

export interface EarningsList {
  items: EarningsItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface WeeklyEarningPoint {
  label: string;
  totalCommission: number;
  totalBookings: number;
  paidCount: number;
  pendingCount: number;
}
