export interface NotificationLogItemDto {
  _id: string;
  notification_type: string;
  recipient_email: string;
  recipient_name: string;
  booking_id: string;
  prop_id: number;
  status: string;
  error_message: string;
  message?: string;
  created_at: string;
}

export interface NotificationStatsDto {
  total: number;
  by_type: Record<string, number>;
  by_status: Record<string, number>;
}

export interface NotificationsListDto {
  items: NotificationLogItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  stats: NotificationStatsDto;
}
