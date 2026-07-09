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
  guestPhone: string;
  cedula: string;
  checkInDate: string;
  checkOutDate: string;
  status: string;
  bookingSource: string;
  assignedRooms: string[];
  roomsAssignedCount: number;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  stayStatus: string;
  folio: string;
  checkInTime: string;
  checkOutTime: string;
  checkInTimeActual: string;
  checkOutTimeActual: string;
  checkInBy: string;
  checkOutBy: string;
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
  checkInTime?: string;
  checkOutTime?: string;
  adults: number;
  children: number;
  rooms: number;
  comment: string;
  couponCode?: string;
  specialRequests?: string[];
  selectedAmenities?: string[];
  roomTypeId?: string;
  ratePlanId?: string;
  /** Payment fields (Phase 1) */
  transactionId?: string;
  paymentMethod?: string;
  cardLast4?: string;
}

/** A rate plan option with pricing for a specific date range */
export interface RatePlanOption {
  ratePlanId: string;
  name: string;
  description: string;
  baseRate: number | null;
  currency: string;
  isActive: boolean;
  avgRatePerNight: number;
  totalPrice: number;
  nights: number;
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
  transactionId?: string;
  paymentMethod?: string;
  cardLast4?: string;
  paymentStatus?: string;
  cancellationPolicy?: string | null;
}

export interface ReservationPreview {
  available: boolean;
  availabilityMessage: string | null;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  cancellationPolicy?: string | null;
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
  transactionId?: string;
  cardLast4?: string;
  paymentStatus?: string;
  cancellationFree?: boolean;
  cancellationPenaltyPercent?: number;
  cancellationPenaltyAmount?: number;
  additionalCharges: Array<{
    concept: string;
    amount: number;
    quantity: number;
    total: number;
    note: string;
    createdAt: string;
  }>;
  assignedRooms: Array<{
    hotelRoomId: string;
    roomNumber: string;
    roomLabel: string;
    floor: string;
    roomStatus: string;
  }>;
  totalCharges: number;
  amenitiesCount: number;
  amenitiesTotal: number;
  history: Array<{
    status: string;
    changedAt: string;
    reason: string;
    changedBy: string;
  }>;
  stayStatus?: string;
}
