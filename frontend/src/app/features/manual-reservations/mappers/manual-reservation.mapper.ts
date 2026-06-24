import type { ManualReservationCreateDto, ManualReservationListItemDto, ManualReservationResultDto, ManualReservationOptionDto, ManualReservationRoomTypeDto } from '../models/manual-reservation.dto';
import type { ManualReservationInput, ManualReservationListItem, ManualReservationResult, HotelOption, RoomTypeOption } from '../models/manual-reservation.model';

export function mapPayload(input: ManualReservationInput): ManualReservationCreateDto {
  return {
    prop_id: input.propId,
    room_type_id: input.roomTypeId,
    guest_name: input.guestName,
    guest_email: input.guestEmail,
    guest_phone: input.guestPhone || undefined,
    check_in_date: input.checkInDate,
    check_out_date: input.checkOutDate,
    adults: input.adults,
    children: input.children,
    rooms: input.rooms,
    comment: input.comment || undefined,
  };
}

export function mapResult(dto: ManualReservationResultDto): ManualReservationResult {
  return {
    bookingId: dto.booking_id,
    status: dto.status,
    totalPrice: dto.total_price,
    currency: dto.currency,
    totalNights: dto.total_nights,
    manualReservationId: dto.manual_reservation_id,
  };
}

export function mapListItem(dto: ManualReservationListItemDto): ManualReservationListItem {
  return {
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    hotelLabel: dto.hotel?.hotel_label ?? `Hotel ${dto.prop_id}`,
    guestName: dto.guest_name,
    guestEmail: dto.guest_email,
    status: dto.status,
    checkInDate: dto.check_in_date,
    checkOutDate: dto.check_out_date,
    adults: dto.adults,
    children: dto.children,
    rooms: dto.rooms,
    totalPrice: dto.total_price,
    currency: dto.currency,
    totalNights: dto.total_nights,
    createdAt: dto.created_at?.slice(0, 10) ?? '',
    createdBy: dto.created_by,
  };
}

export function mapHotelOption(dto: ManualReservationOptionDto): HotelOption {
  return {
    propId: dto.prop_id,
    label: dto.display_name,
  };
}

export function mapRoomTypeOption(dto: ManualReservationRoomTypeDto): RoomTypeOption {
  return {
    roomTypeId: dto.room_type_id,
    name: dto.name,
    maxAdults: dto.max_adults,
    maxChildren: dto.max_children,
    baseCapacity: dto.base_capacity,
  };
}
