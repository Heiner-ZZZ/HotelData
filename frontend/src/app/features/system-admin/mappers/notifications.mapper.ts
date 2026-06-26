import type { NotificationLogItemDto, NotificationsListDto } from '../models/notifications.dto';
import type { NotificationLogItem, NotificationsViewModel } from '../models/notifications.model';

const TYPE_LABELS: Record<string, string> = {
  staff_new_booking: 'Staff — Nueva reserva',
  staff_check_in: 'Staff — Check-in',
  staff_check_out: 'Staff — Check-out',
  guest_confirmed: 'Cliente — Confirmada',
  guest_rejected: 'Cliente — Rechazada',
  guest_cancelled: 'Cliente — Cancelada',
  guest_modified: 'Cliente — Modificada',
  guest_checked_in: 'Cliente — Check-in',
  guest_checked_out: 'Cliente — Check-out',
  guest_invoice_issued: 'Cliente — Factura emitida',
  guest_other: 'Cliente — Otro',
};

const STATUS_MAP: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' }> = {
  sent: { label: 'Enviado', tone: 'success' },
  failed: { label: 'Fallido', tone: 'warning' },
  error: { label: 'Error', tone: 'danger' }
};

function mapNotificationItem(dto: NotificationLogItemDto): NotificationLogItem {
  const statusConfig = STATUS_MAP[dto.status] || { label: dto.status, tone: 'warning' as const };
  return {
    notificationType: dto.notification_type,
    recipientEmail: dto.recipient_email,
    recipientName: dto.recipient_name,
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    status: dto.status,
    errorMessage: dto.error_message || '',
    createdAt: dto.created_at,
    typeLabel: TYPE_LABELS[dto.notification_type] || dto.notification_type,
    statusLabel: statusConfig.label,
    statusTone: statusConfig.tone
  };
}

export function mapNotificationsList(dto: NotificationsListDto): NotificationsViewModel {
  return {
    items: dto.items.map(mapNotificationItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
    stats: {
      total: dto.stats.total,
      byType: dto.stats.by_type,
      byStatus: dto.stats.by_status
    }
  };
}
