import type { CheckOutsDto } from '../models/check-outs.dto';
import type { CheckOutsViewModel } from '../models/check-outs.model';

export function mapCheckOuts(dto: CheckOutsDto): CheckOutsViewModel {
  return {
    operationDate: dto.operation_date,
    propId: dto.prop_id,
    propertyOptions: dto.property_options.map((item) => ({
      propId: item.prop_id,
      label: item.label || `Hotel ${item.prop_id}`
    })),
    departuresToday: dto.summary.departures_today,
    pendingCount: dto.summary.pending,
    completedCount: dto.summary.completed,
    cancelledOrNoShowCount: dto.summary.cancelled_or_no_show,
    items: dto.items.map((item) => ({
      bookingId: item.booking_id,
      propId: item.prop_id,
      hotelLabel: item.hotel_label,
      guestName: item.guest_name,
      guestEmail: item.guest_email,
      date: item.date,
      reservationStatusLabel: item.reservation_status_label,
      stayStatusLabel: item.stay_status_label,
      roomsLabel: item.rooms_label,
      estimatedTime: item.estimated_time,
      balanceLabel: item.balance_label,
      notes: item.notes,
      canComplete: item.can_complete
    }))
  };
}
