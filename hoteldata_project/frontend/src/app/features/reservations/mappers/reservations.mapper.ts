import { formatDateTime } from '../../../shared/utils/date-format.util';
import type {
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationListItemDto,
  ReservationOptionsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type {
  ReservationCreateInput,
  ReservationDetailViewModel,
  ReservationHotelOption,
  ReservationListItem,
  ReservationsListViewModel
} from '../models/reservations.model';

function mapReservationListItem(item: ReservationListItemDto): ReservationListItem {
  return {
    bookingId: item.booking_id,
    propId: item.prop_id,
    hotelLabel: item.hotel?.hotel_label || `Hotel ${item.prop_id}`,
    guestName: item.guest_name,
    guestEmail: item.guest_email,
    checkInDate: item.check_in_date,
    checkOutDate: item.check_out_date,
    status: item.status,
    bookingSource: item.booking_source
  };
}

export function mapReservationsList(dto: ReservationsListDto): ReservationsListViewModel {
  return {
    items: dto.items.map(mapReservationListItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next
  };
}

export function mapReservationOptions(dto: ReservationOptionsDto): ReservationHotelOption[] {
  return dto.hotel_options.map((item) => ({
    propId: item.prop_id,
    label: item.label
  }));
}

export function mapReservationCreatePayload(input: ReservationCreateInput) {
  return {
    prop_id: input.propId,
    guest_name: input.guestName,
    guest_email: input.guestEmail,
    check_in_date: input.checkInDate,
    check_out_date: input.checkOutDate,
    adults: input.adults,
    children: input.children,
    rooms: input.rooms,
    comment: input.comment
  };
}

export function mapReservationCreateResult(dto: ReservationCreateDto) {
  return {
    bookingId: dto.booking_id,
    status: dto.status,
    manualReservationId: dto.manual_reservation_id
  };
}

export function mapReservationDetail(dto: ReservationDetailDto): ReservationDetailViewModel {
  return {
    bookingId: dto.booking.booking_id,
    status: dto.booking.status,
    bookingSource: dto.booking.booking_source,
    hotelLabel: dto.hotel?.hotel_label || `Hotel ${dto.booking.prop_id}`,
    propId: dto.booking.prop_id,
    checkInDate: dto.booking.check_in_date,
    checkOutDate: dto.booking.check_out_date,
    occupancyLabel: `${dto.booking.adults} adultos · ${dto.booking.children} niños · ${dto.booking.rooms} habitaciones`,
    comment: dto.booking.comment || 'N/D',
    createdAt: formatDateTime(dto.booking.created_at),
    guestName: dto.guest?.guest_name || dto.booking.guest_name,
    guestEmail: dto.guest?.guest_email || dto.booking.guest_email,
    isManual: Boolean(dto.manual),
    manualReservationId: dto.manual?.manual_reservation_id || null,
    canCancel: dto.can_cancel,
    history: dto.history.map((item) => ({
      status: item.status,
      changedAt: formatDateTime(item.changed_at),
      reason: item.reason,
      changedBy: item.changed_by
    }))
  };
}
