import type { ClientNotificationDto, MyNotificationsDto } from '../models/notifications.dto';
import type { ClientNotification, MyNotifications } from '../models/notifications.model';

function mapNotification(dto: ClientNotificationDto): ClientNotification {
  return {
    id: dto._id || '',
    notificationType: dto.notification_type,
    typeLabel: dto.type_label,
    recipientEmail: dto.recipient_email,
    recipientName: dto.recipient_name || '',
    bookingId: dto.booking_id || '',
    propId: dto.prop_id || 0,
    status: dto.status || '',
    statusLabel: dto.status_label || dto.status,
    statusTone: (dto.status_tone as ClientNotification['statusTone']) || 'neutral',
    errorMessage: dto.error_message || '',
    message: dto.message || '',
    title: dto.title || '',
    createdAt: dto.created_at_iso || '',
    isUnread: dto.is_unread ?? false,
  };
}

export function mapMyNotifications(dto: MyNotificationsDto): MyNotifications {
  return {
    items: (dto.items || []).map(mapNotification),
    total: dto.total || 0,
    unreadCount: dto.unread_count || 0,
    page: dto.page || 1,
    pageSize: dto.page_size || 20,
    totalPages: dto.total_pages || 1,
  };
}
