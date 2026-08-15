export interface ClientNotification {
  /** Id Mongo de la fila en notification_log (para marcar como leída). */
  id: string;
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
  message: string;
  /** Título de la promoción (solo guest_promotional). */
  title: string;
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
