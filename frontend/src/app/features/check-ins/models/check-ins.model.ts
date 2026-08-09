export interface CheckInPropertyOption {
  propId: number;
  label: string;
}

export interface CheckInRowViewModel {
  bookingId: string;
  propId: number;
  hotelLabel: string;
  guestName: string;
  guestEmail: string;
  date: string;
  checkInDate: string;
  checkInTime: string;
  checkOutDate: string;
  reservationStatusLabel: string;
  stayStatusLabel: string;
  roomsLabel: string;
  assignedRooms: string[];
  assignedRoomNumbers: string[];
  roomNumbersLabel: string[];
  estimatedTime: string;
  /** Hora estimada de llegada del huésped (HH:MM) si la declaró al reservar. */
  estimatedArrivalTime: string;
  /** Marcador de late check-in (llegada tarde). */
  lateCheckin: boolean;
  notes: string;
  canComplete: boolean;
}

export interface CheckInsViewModel {
  operationDate: string;
  propId: number | null;
  propertyOptions: CheckInPropertyOption[];
  arrivalsToday: number;
  pendingCount: number;
  completedCount: number;
  cancelledOrNoShowCount: number;
  items: CheckInRowViewModel[];
}
