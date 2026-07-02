export interface ClientNotification {
  notificationType: string;
  typeLabel: string;
  recipientEmail: string;
  recipientName: string;
  bookingId: string;
  propId: number;
  status: string;
  statusLabel: string;
  statusTone: string;
  isUnread: boolean;
  errorMessage: string;
  createdAt: string;
}

export interface MyNotifications {
  items: ClientNotification[];
  total: number;
  unreadCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
}
