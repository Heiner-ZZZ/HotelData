import type { CheckInsDto } from '../models/check-ins.dto';
import type { CheckInsViewModel } from '../models/check-ins.model';

export function mapCheckIns(dto: CheckInsDto): CheckInsViewModel {
  return {
    operationDate: dto.operation_date,
    propId: dto.prop_id,
    propertyOptions: dto.property_options.map((item) => ({
      propId: item.prop_id,
      label: item.label || `Hotel ${item.prop_id}`
    })),
    arrivalsToday: dto.summary.arrivals_today,
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
      checkInDate: item.check_in_date,
      checkInTime: item.check_in_time,
      checkOutDate: item.check_out_date,
      reservationStatusLabel: item.reservation_status_label,
      stayStatusLabel: item.stay_status_label,
      roomsLabel: item.rooms_label,
      assignedRooms: item.assigned_rooms || [],
      assignedRoomNumbers: item.assigned_room_numbers || [],
      roomNumbersLabel: item.room_numbers_label || [],
      estimatedTime: item.estimated_time,
      notes: item.notes,
      canComplete: item.can_complete
    }))
  };
}
