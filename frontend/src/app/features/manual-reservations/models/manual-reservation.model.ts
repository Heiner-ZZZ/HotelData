export interface ManualReservationListItem {
  bookingId: string;
  propId: number;
  hotelLabel: string;
  guestName: string;
  guestEmail: string;
  status: string;
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  rooms: number;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  createdAt: string;
  createdBy: string;
}

export interface ManualReservationInput {
  propId: number;
  roomTypeId: string;
  guestName: string;
  guestEmail: string;
  guestPhone: string;
  checkInDate: string;
  checkOutDate: string;
  adults: number;
  children: number;
  rooms: number;
  comment: string;
}

export interface ManualReservationResult {
  bookingId: string;
  status: string;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  manualReservationId: string | null;
}

export interface HotelOption {
  propId: number;
  label: string;
}

export interface RoomTypeOption {
  roomTypeId: string;
  name: string;
  maxAdults: number;
  maxChildren: number;
  baseCapacity: number;
}
