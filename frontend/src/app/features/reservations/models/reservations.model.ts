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
  guestPhone: string;
  cedula?: string;
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  rooms: number;
  comment: string;
  couponCode?: string;
  specialRequests?: string[];
}

export interface ReservationCreateResult {
  bookingId: string;
  status: string;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  manualReservationId: string | null;
  hotelLabel: string;
  hotelPropId: number;
  roomTypeName: string | null;
  checkInDate: string;
  checkOutDate: string;
  rooms: number;
  adults: number;
  children: number;
  guestName: string;
  guestEmail: string;
  discountPercent?: number | null;
  originalTotalPrice?: number | null;
}

export interface ReservationPreview {
  available: boolean;
  availabilityMessage: string | null;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
}

export interface ReservationStats {
  pending: number;
  confirmed: number;
  cancelled: number;
  rejected: number;
  checkedIn: number;
  checkedOut: number;
  total: number;
  active: number;
  completed: number;
  lost: number;
}

export interface NightBreakdown {
  date: string;
  rate: number;
  rooms: number;
  nightTotal: number;
}

export interface PriceBreakdown {
  nights: NightBreakdown[];
  subtotal: number;
  taxes: number;
  ivaRate: number;
  total: number;
  currency: string;
  source: string;
}

export interface RoomTypeInfo {
  roomTypeId: string;
  name: string;
}

export interface InvoiceSummary {
  id: string;
  invoiceNumber: string;
  subtotal: number;
  taxes: number;
  total: number;
  status: string;
  issuedAt: string | null;
  paidAt: string | null;
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
  rooms: number;
  comment: string;
  createdAt: string;
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  guestCedula: string;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  discountPercent?: number | null;
  originalTotalPrice?: number | null;
  specialRequests?: string[];
  isManual: boolean;
  manualReservationId: string | null;
  canCancel: boolean;
  canConfirm: boolean;
  canReject: boolean;
  invoice: InvoiceSummary | null;
  roomType: RoomTypeInfo | null;
  priceBreakdown: PriceBreakdown | null;
  cancellationPolicy: string | null;
  history: Array<{
    status: string;
    changedAt: string;
    reason: string;
    changedBy: string;
  }>;
}
