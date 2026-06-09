export interface ReservationsListViewModel {
  items: ReservationListItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface ReservationListItem {
  bookingId: string;
  propId: number;
  hotelLabel: string;
  guestName: string;
  guestEmail: string;
  checkInDate: string;
  checkOutDate: string;
  status: string;
  bookingSource: string;
}

export interface ReservationHotelOption {
  propId: number;
  label: string;
}

export interface ReservationCreateInput {
  propId: number;
  guestName: string;
  guestEmail: string;
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  rooms: number;
  comment: string;
}

export interface ReservationDetailViewModel {
  bookingId: string;
  status: string;
  bookingSource: string;
  hotelLabel: string;
  propId: number;
  checkInDate: string;
  checkOutDate: string;
  occupancyLabel: string;
  comment: string;
  createdAt: string;
  guestName: string;
  guestEmail: string;
  isManual: boolean;
  manualReservationId: string | null;
  canCancel: boolean;
  history: Array<{
    status: string;
    changedAt: string;
    reason: string;
    changedBy: string;
  }>;
}
