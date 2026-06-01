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
  reservationStatusLabel: string;
  stayStatusLabel: string;
  roomsLabel: string;
  estimatedTime: string;
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
