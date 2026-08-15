/** A single reservation bar in the reception calendar. */
export interface ReceptionCalendarReservation {
  bookingId: string;
  guestName: string;
  adults: number;
  children: number;
  checkInDate: string;
  checkInTime: string;
  /** Hora estimada de llegada (HH:MM) si el huésped la declaró. */
  estimatedArrivalTime: string;
  /** Marcador de late check-in visible en la barra del calendario. */
  lateCheckin: boolean;
  checkOutDate: string;
  checkOutTime: string;
  totalNights: number;
  status: string;
  /** stay_status del booking (no_show, pending, checked_in, …). */
  stayStatus: string;
  visualStatus: 'active' | 'upcoming' | 'past' | 'cancelled';
  /**
   * Ventana de reapertura de no-show (server-authoritative, misma regla que
   * ``reopen_no_show``): ``'open'`` = reabrible (hoy/ayer + estadía vigente),
   * ``'too_late'``/``'stay_ended'`` = ventana cerrada, ``null`` = no aplica.
   */
  reopenWindow: 'open' | 'too_late' | 'stay_ended' | null;
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
  floor: string;
  reservations: ReceptionCalendarReservation[];
}

/** Full reception calendar response — one row per physical room. */
export interface ReceptionCalendarData {
  rooms: ReceptionCalendarRoom[];
  startDate: string;
  endDate: string;
  today: string;
  /** Hotel-wide policy defaults (HH:MM) used to prefill a new reservation. */
  checkInTime: string;
  checkOutTime: string;
}

/** A computed day cell in the calendar grid. */
export interface ReceptionCalendarDay {
  date: string;
  day: number;
  dayName: string;
  isToday: boolean;
  isWeekend: boolean;
}
