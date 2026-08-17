import { formatDateTime } from '../../../shared/utils/date-format.util';
import type {
  AssignedRoomSnapshotDto,
  ReservationCreateDto,
  ReservationDetailDto,
  ReservationListItemDto,
  ReservationOptionsDto,
  ReservationPreviewDto,
  ReservationStatsDto,
  ReservationsListDto
} from '../models/reservations.dto';
import type {
  AssignedRoomView,
  ReservationCreateInput,
  ReservationDetailViewModel,
  ReservationHotelOption,
  ReservationListItem,
  ReservationStats,
  ReservationsListViewModel
} from '../models/reservations.model';

/**
 * Normalize backend `assigned_rooms` item (dict or legacy string) →
 * AssignedRoomView. Tolerates the `@model_validator` backward-compat path
 * where pre-migration bookings may emit a bare string.
 */
function toAssignedRoomView(r: AssignedRoomSnapshotDto | string): AssignedRoomView {
  if (typeof r === 'string') {
    return { hotelRoomId: r, roomNumber: '', roomLabel: '', floor: '', roomStatus: '' };
  }
  return {
    hotelRoomId: r.hotel_room_id,
    roomNumber: r.room_number ?? '',
    roomLabel: r.room_label ?? '',
    floor: r.floor ?? '',
    roomStatus: r.room_status ?? '',
  };
}

function mapFulfillmentItem(f: { label: string; status: string; fulfilled_at?: string | null }): {
  label: string;
  status: 'pending' | 'fulfilled';
  fulfilledAt?: string | null;
} {
  return {
    label: f.label,
    status: f.status === 'fulfilled' ? ('fulfilled' as const) : ('pending' as const),
    fulfilledAt: f.fulfilled_at ?? null,
  };
}

function mapReservationListItem(item: ReservationListItemDto): ReservationListItem {
  const assigned: AssignedRoomView[] = (item.assigned_rooms ?? []).map(toAssignedRoomView);
  return {
    bookingId: item.booking_id,
    propId: item.prop_id,
    hotelLabel: item.hotel?.hotel_label || `Hotel ${item.prop_id}`,
    guestName: item.guest_name,
    guestEmail: item.guest_email,
    guestPhone: item.guest_phone || '',
    cedula: item.cedula || '',
    checkInDate: item.check_in_date,
    checkOutDate: item.check_out_date,
    status: item.status,
    bookingSource: item.booking_source,
    assignedRooms: assigned,
    roomsAssignedCount: assigned.length,
    totalPrice: item.total_price ?? null,
    currency: item.currency || 'USD',
    totalNights: item.total_nights || 0,
    stayStatus: item.stay_status || '',
    reopenWindow: item.reopen_window ?? null,
    noShowReopenedAt: item.no_show_reopened_at ?? null,
    folio: item.folio || '',
    checkInTime: item.check_in_time || '',
    checkOutTime: item.check_out_time || '',
    checkInTimeActual: item.check_in_time_actual || '',
    checkOutTimeActual: item.check_out_time_actual || '',
    checkInBy: item.check_in_by || '',
    checkOutBy: item.check_out_by || '',
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
    estimated_arrival_time: input.estimatedArrivalTime || '',
    adults: input.adults,
    children: input.children,
    rooms: input.rooms,
    comment: input.comment,
    coupon_code: input.couponCode,
    special_requests: input.specialRequests || [],
    selected_amenities: input.selectedAmenities || [],
    room_type_id: input.roomTypeId || '',
    hotel_room_id: input.hotelRoomId || '',
    rate_plan_id: input.ratePlanId || '',
    deposit: input.deposit
      ? {
          amount: input.deposit.amount,
          method: input.deposit.method,
          reference: input.deposit.reference || '',
        }
      : undefined,
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
    transactionId: dto.transaction_id,
    paymentMethod: dto.payment_method,
    cardLast4: dto.card_last4,
    paymentStatus: dto.payment_status,
    cancellationPolicy: dto.cancellation_policy,
  };
}

export function mapReservationPreview(dto: ReservationPreviewDto) {
  return {
    available: dto.available,
    availabilityMessage: dto.availability_message,
    totalPrice: dto.total_price,
    currency: dto.currency,
    totalNights: dto.total_nights,
    taxRate: dto.tax_rate,
    taxAmount: dto.tax_amount,
    taxIncluded: dto.tax_included,
    cancellationPolicy: dto.cancellation_policy,
    depositRequired: dto.deposit_required,
    depositPercent: dto.deposit_percent,
    minDepositAmount: dto.min_deposit_amount,
    priceBreakdown: dto.price_breakdown
      ? {
          baseNightlyRate: dto.price_breakdown.base_nightly_rate,
          nights: dto.price_breakdown.nights,
          baseTotal: dto.price_breakdown.base_total,
          includedAmenities: (dto.price_breakdown.included_amenities || []).map(a => ({
            label: a.label,
            unitPrice: a.unit_price,
          })),
          selectedExtras: (dto.price_breakdown.selected_extras || []).map(a => ({
            label: a.label,
            unitPrice: a.unit_price,
          })),
          amenityTotal: dto.price_breakdown.amenity_total,
          ratePlanName: dto.price_breakdown.rate_plan_name,
          subtotal: dto.price_breakdown.subtotal,
          taxAmount: dto.price_breakdown.tax_amount,
          taxRate: dto.price_breakdown.tax_rate,
          taxIncluded: dto.price_breakdown.tax_included,
          total: dto.price_breakdown.total,
          grandTotal: dto.price_breakdown.grand_total,
        }
      : null,
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
  // Backend wire-shape tolerance: `GET /reservations/{id}` historically returned a
  // nested envelope (`{ booking, guest, hotel, ... }`), but the live endpoint
  // (after the booking_orders collection flattening) emits top-level snake_case
  // fields directly — e.g. `{ booking_id, prop_id, status, ... }`. Old `backend/
  // /reservations/{id}/cancel-preview` accidentally fed DTOs declared flat into
  // the same mapper. Reading `dto.booking.booking_id` against a flat wire throws
  // TypeError, which surfaced as "No fue posible cargar la reserva".
  //
  // Bilingual: read nested first; fall back to flat top-level. Same shape for
  // the optional `guest` doc. Single source of truth for downstream consumers.
  const wire = dto as unknown as {
    booking_id?: string;
    prop_id?: number;
    status?: string;
    booking_source?: string;
    guest_name?: string;
    guest_email?: string;
    guest_phone?: string;
    room_type_id?: string;
    check_in_date?: string;
    check_out_date?: string;
    check_in_time?: string;
    check_out_time?: string;
    adults?: number;
    children?: number;
    rooms?: number;
    comment?: string;
    total_price?: number | null;
    currency?: string;
    total_nights?: number;
    created_at?: string;
    hotel_id?: string;
    rate_plan_id?: string;
    stay_status?: string | null;
    check_out_mode?: string | null;
    late_checkout_minutes?: number | null;
    late_checkout_policy_time?: string | null;
    check_out_date_actual?: string | null;
    check_out_time_actual?: string | null;
    coupon_code?: string;
    special_requests?: string[] | string;
    estimated_arrival_time?: string;
    late_checkin?: boolean;
    discount_percent?: number | null;
    original_total_price?: number | null;
    transaction_id?: string;
    card_last4?: string;
    payment_status?: string;
    deposit?: {
      amount: number;
      method: string;
      reference?: string;
      status: string;
      paid_at?: string | null;
    } | null;
    cancellation_free?: boolean;
    cancellation_penalty_percent?: number;
    cancellation_penalty_amount?: number;
    cedula?: string;
    can_cancel?: boolean;
    amenities_count?: number;
    amenities_total?: number;
  };
  const booking = dto.booking ?? wire;
  const guest = dto.guest ?? wire;
  /** Backend splits `special_requests` with `|` when flattening from flat wire,
   *  whereas nested wire keeps it as a `string[]`. Normalise to string[].
   *  `raw` is typed `unknown` first to avoid TS narrowing `raw` to `never`
   *  after the `Array.isArray` early-return chain — its true union
   *  (`string[] | string | undefined`) collapses under strict narrowing. */
  const specialRequests: string[] = (() => {
    const raw: unknown = booking.special_requests;
    if (Array.isArray(raw)) return raw as string[];
    if (typeof raw === 'string' && raw.length > 0) {
      return raw.split('|').map((s: string) => s.trim()).filter((s: string) => Boolean(s));
    }
    return [];
  })();
  return {
    bookingId: booking.booking_id ?? '',
    status: booking.status ?? '',
    bookingSource: booking.booking_source ?? '',
    hotelLabel: dto.hotel?.hotel_label || `Hotel ${booking.prop_id ?? 0}`,
    propId: booking.prop_id ?? 0,
    checkInDate: booking.check_in_date ?? '',
    checkOutDate: booking.check_out_date ?? '',
    occupancyLabel: `${booking.adults ?? 0} adultos · ${booking.children ?? 0} niños · ${booking.rooms ?? 0} habitaciones`,
    rooms: booking.rooms ?? 0,
    comment: booking.comment || 'N/D',
    createdAt: formatDateTime(booking.created_at ?? ''),
    guestName: guest.guest_name ?? '',
    guestEmail: guest.guest_email ?? '',
    guestPhone: guest.guest_phone ?? '',
    guestCedula: guest.cedula ?? '',
    totalPrice: booking.total_price ?? null,
    currency: booking.currency || 'USD',
    totalNights: booking.total_nights ?? 0,
    discountPercent: booking.discount_percent,
    originalTotalPrice: booking.original_total_price,
    specialRequests,
    selectedAmenities: Array.isArray(booking.selected_amenities) ? booking.selected_amenities : [],
    estimatedArrivalTime: booking.estimated_arrival_time ?? '',
    lateCheckin: Boolean(booking.late_checkin),
    checkOutMode: booking.check_out_mode ?? null,
    lateCheckoutMinutes: Number(booking.late_checkout_minutes ?? 0),
    lateCheckoutPolicyTime: booking.late_checkout_policy_time ?? '',
    checkOutDateActual: booking.check_out_date_actual ?? null,
    checkOutTimeActual: booking.check_out_time_actual ?? null,
    specialRequestFulfillment: Array.isArray(dto.special_request_fulfillment)
      ? dto.special_request_fulfillment.map(mapFulfillmentItem)
      : undefined,
    amenityFulfillment: Array.isArray(dto.amenity_fulfillment)
      ? dto.amenity_fulfillment.map(mapFulfillmentItem)
      : undefined,
    isManual: Boolean(dto.manual),
    manualReservationId: dto.manual?.manual_reservation_id ?? null,
    canCancel: wire.can_cancel ?? false,
    canConfirm: false,
    canReject: false,
    invoice: dto.invoice ? {
      id: dto.invoice.id || (dto.invoice as unknown as { _id?: string })._id || '',
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
    cancellationPolicy: dto.cancellation_policy ?? null,
    transactionId: booking.transaction_id,
    cardLast4: booking.card_last4,
    paymentStatus: booking.payment_status,
    // Depósito REAL (billing, shift-gated) — reemplaza a la tarjeta ficticia
    // del stub eliminado. Leído del wire plano del endpoint de detalle.
    deposit: wire.deposit
      ? {
          amount: wire.deposit.amount,
          method: wire.deposit.method,
          reference: wire.deposit.reference || '',
          status: wire.deposit.status,
          paidAt: wire.deposit.paid_at ?? null,
        }
      : null,
    cancellationFree: booking.cancellation_free,
    cancellationPenaltyPercent: booking.cancellation_penalty_percent,
    cancellationPenaltyAmount: booking.cancellation_penalty_amount,
    additionalCharges: (dto.additional_charges ?? []).map(c => ({
      concept: c.concept,
      amount: c.amount,
      quantity: c.quantity,
      total: c.total,
      note: c.note || '',
      createdAt: c.created_at,
    })),
    assignedRooms: (dto.assigned_rooms ?? []).map(toAssignedRoomView),
    totalCharges: (dto.additional_charges ?? []).reduce((sum, c) => sum + (c.total ?? 0), 0),
    amenitiesCount: wire.amenities_count ?? 0,
    amenitiesTotal: wire.amenities_total ?? 0,
    history: (dto.history ?? []).map((item) => ({
      status: item.status,
      changedAt: formatDateTime(item.changed_at),
      reason: item.reason,
      changedBy: item.changed_by,
    })),
    // stay_status is the operational stay phase (checked_in, checked_out, etc.)
    // It is NOT a fallback for booking.status. If undefined, leave undefined.
    // The frontend should use `effectiveStayStatus()` from reservation-status.util
    // when it needs a combined fallback value.
    stayStatus: booking.stay_status ?? undefined,
  };
}
