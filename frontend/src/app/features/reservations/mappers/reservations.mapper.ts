import { formatDateTime } from '../../../shared/utils/date-format.util';
import type {
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationListItemDto,
  ReservationOptionsDto,
  ReservationPreviewDto,
  ReservationStatsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type {
  ReservationCreateInput,
  ReservationDetailViewModel,
  ReservationHotelOption,
  ReservationListItem,
  ReservationStats,
  ReservationsListViewModel
} from '../models/reservations.model';

function mapReservationListItem(item: ReservationListItemDto): ReservationListItem {
  const assigned: string[] = item.assigned_rooms || [];
  return {
    bookingId: item.booking_id,
    propId: item.prop_id,
    hotelLabel: item.hotel?.hotel_label || `Hotel ${item.prop_id}`,
    guestName: item.guest_name,
    guestEmail: item.guest_email,
    checkInDate: item.check_in_date,
    checkOutDate: item.check_out_date,
    status: item.status,
    bookingSource: item.booking_source,
    assignedRooms: assigned,
    roomsAssignedCount: assigned.length,
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
    guest_phone: input.guestPhone,
    cedula: input.cedula || '',
    check_in_date: input.checkInDate,
    check_out_date: input.checkOutDate,
    check_in_time: input.checkInTime || '',
    check_out_time: input.checkOutTime || '',
    adults: input.adults,
    children: input.children,
    rooms: input.rooms,
    comment: input.comment,
    coupon_code: input.couponCode,
    special_requests: input.specialRequests || [],
    selected_amenities: input.selectedAmenities || [],
    room_type_id: input.roomTypeId || ''
  };
}

export function mapReservationCreateResult(dto: ReservationCreateDto) {
  return {
    bookingId: dto.booking_id,
    status: dto.status,
    totalPrice: dto.total_price,
    currency: dto.currency,
    totalNights: dto.total_nights,
    manualReservationId: dto.manual_reservation_id,
    hotelLabel: dto.hotel_label,
    hotelPropId: dto.hotel_prop_id,
    roomTypeName: dto.room_type_name,
    checkInDate: dto.check_in_date,
    checkOutDate: dto.check_out_date,
    rooms: dto.rooms,
    adults: dto.adults,
    children: dto.children,
    guestName: dto.guest_name,
    guestEmail: dto.guest_email,
    discountPercent: dto.discount_percent,
    originalTotalPrice: dto.original_total_price,
  };
}

export function mapReservationPreview(dto: ReservationPreviewDto) {
  return {
    available: dto.available,
    availabilityMessage: dto.availability_message,
    totalPrice: dto.total_price,
    currency: dto.currency,
    totalNights: dto.total_nights
  };
}

export function mapReservationStats(dto: ReservationStatsDto): ReservationStats {
  return {
    pending: dto.pending,
    confirmed: dto.confirmed,
    cancelled: dto.cancelled,
    rejected: dto.rejected,
    checkedIn: dto.checked_in,
    checkedOut: dto.checked_out,
    total: dto.total,
    active: dto.active,
    completed: dto.completed,
    lost: dto.lost
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
    rooms: dto.booking.rooms,
    comment: dto.booking.comment || 'N/D',
    createdAt: formatDateTime(dto.booking.created_at),
    guestName: dto.guest?.guest_name || dto.booking.guest_name,
    guestEmail: dto.guest?.guest_email || dto.booking.guest_email,
    guestPhone: dto.guest?.guest_phone || dto.booking.guest_phone || '',
    guestCedula: dto.guest?.cedula || '',
    totalPrice: dto.booking.total_price ?? null,
    currency: dto.booking.currency || 'USD',
    totalNights: dto.booking.total_nights || 0,
    discountPercent: dto.booking.discount_percent,
    originalTotalPrice: dto.booking.original_total_price,
    specialRequests: dto.booking.special_requests || [],
    isManual: Boolean(dto.manual),
    manualReservationId: dto.manual?.manual_reservation_id || null,
    canCancel: dto.can_cancel,
    canConfirm: false,
    canReject: false,
    invoice: dto.invoice ? {
      id: (dto.invoice as any).id || (dto.invoice as any)._id,
      invoiceNumber: dto.invoice.invoice_number,
      subtotal: dto.invoice.subtotal,
      taxes: dto.invoice.taxes,
      total: dto.invoice.total,
      status: dto.invoice.status,
      issuedAt: dto.invoice.issued_at,
      paidAt: dto.invoice.paid_at,
    } : null,
    roomType: dto.room_type ? {
      roomTypeId: dto.room_type.room_type_id,
      name: dto.room_type.name,
    } : null,
    priceBreakdown: dto.price_breakdown ? {
      nights: dto.price_breakdown.nights.map(n => ({
        date: n.date,
        rate: n.rate,
        rooms: n.rooms,
        nightTotal: n.night_total,
      })),
      subtotal: dto.price_breakdown.subtotal,
      taxes: dto.price_breakdown.taxes,
      ivaRate: dto.price_breakdown.iva_rate,
      total: dto.price_breakdown.total,
      currency: dto.price_breakdown.currency,
      source: dto.price_breakdown.source,
    } : null,
    cancellationPolicy: dto.cancellation_policy || null,
    additionalCharges: (dto.additional_charges || []).map(c => ({
      concept: c.concept,
      amount: c.amount,
      quantity: c.quantity,
      total: c.total,
      note: c.note || '',
      createdAt: c.created_at,
    })),
    assignedRooms: (dto.assigned_rooms || []).map(r => ({
      hotelRoomId: r.hotel_room_id,
      roomNumber: r.room_number,
      roomLabel: r.room_label,
      floor: r.floor,
      roomStatus: r.room_status,
    })),
    totalCharges: (dto.additional_charges || []).reduce((sum, c) => sum + (c.total || 0), 0),
    amenitiesCount: dto.amenities_count || 0,
    amenitiesTotal: dto.amenities_total || 0,
    history: dto.history.map((item) => ({
      status: item.status,
      changedAt: formatDateTime(item.changed_at),
      reason: item.reason,
      changedBy: item.changed_by
    })),
    stayStatus: dto.booking.stay_status || dto.booking.status,
  };
}
