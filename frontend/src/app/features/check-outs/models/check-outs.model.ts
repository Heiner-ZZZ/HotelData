export interface CheckOutPropertyOption {
  propId: number;
  label: string;
}

export interface CheckOutRowViewModel {
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
  totalPrice: number;
  balanceLabel: string;
  notes: string;
  canComplete: boolean;
}

export interface CheckOutsViewModel {
  operationDate: string;
  propId: number | null;
  propertyOptions: CheckOutPropertyOption[];
  departuresToday: number;
  pendingCount: number;
  completedCount: number;
  cancelledOrNoShowCount: number;
  items: CheckOutRowViewModel[];
}
