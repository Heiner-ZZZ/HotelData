/** A single reservation bar in the reception calendar. */
export interface ReceptionCalendarReservation {
  bookingId: string;
  guestName: string;
  adults: number;
  children: number;
  checkInDate: string;
  checkInTime: string;
  checkInFraction: number;   // 0.0–1.0 — partial-day positioning
  checkOutDate: string;
  checkOutTime: string;
  checkOutFraction: number;  // 0.0–1.0 — partial-day positioning
  totalNights: number;
  status: string;
  visualStatus: 'active' | 'upcoming' | 'past' | 'cancelled';
  assignedRooms: string[];
  hotelRoomId: string;
  roomNumber: string;
  totalPrice: number | null;
  currency: string;
}

/** A single physical room in the reception calendar. */
export interface ReceptionCalendarRoom {
  roomNumber: string;
  hotelRoomId: string;
  roomTypeName: string;
  roomTypeId: string;
  reservations: ReceptionCalendarReservation[];
}

/** Full reception calendar response — one row per physical room. */
export interface ReceptionCalendarData {
  rooms: ReceptionCalendarRoom[];
  startDate: string;
  endDate: string;
  today: string;
}

/** A computed day cell in the calendar grid. */
export interface ReceptionCalendarDay {
  date: string;
  day: number;
  dayName: string;
  isToday: boolean;
  isWeekend: boolean;
}
