export interface NotificationLogItem {
  id: string;
  notificationType: string;
  recipientEmail: string;
  recipientName: string;
  bookingId: string;
  propId: number;
  status: string;
  errorMessage: string;
  message: string;
  createdAt: string;
  typeLabel: string;
  statusLabel: string;
  statusTone: 'success' | 'warning' | 'danger';
}

export interface NotificationStats {
  total: number;
  byType: Record<string, number>;
  byStatus: Record<string, number>;
}

export interface NotificationsViewModel {
  items: NotificationLogItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  stats: NotificationStats;
}
