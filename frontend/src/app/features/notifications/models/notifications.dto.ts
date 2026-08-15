export interface ClientNotificationDto {
  _id: string;
  notification_type: string;
  type_label: string;
  recipient_email: string;
  recipient_name: string;
  booking_id: string;
  prop_id: number;
  status: string;
  status_label: string;
  status_tone: string;
  message: string;
  /** Título de la promoción (solo guest_promotional; vacío en transaccionales). */
  title?: string;
  is_unread?: boolean;
  error_message: string;
  created_at_iso: string;
}

export interface MyNotificationsDto {
  items: ClientNotificationDto[];
  total: number;
  unread_count: number;
  page: number;
  page_size: number;
  total_pages: number;
}
