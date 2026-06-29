export interface GuestAmenityBookingDto {
  booking_id: string;
  guest_name: string;
  check_in: string;
  check_out: string;
  status: string;
  hotel_label: string;
}

export interface GuestAmenityItemDto {
  label: string;
  active: boolean;
  unit_price: number;
  available_stock?: number;
}

export interface GuestAmenityCategoryDto {
  category: string;
  items: GuestAmenityItemDto[];
}

export interface GuestAmenityCatalogDto {
  booking: GuestAmenityBookingDto;
  catalog: GuestAmenityCategoryDto[];
  active_amenities: string[];
}

export interface GuestAmenityRequestItem {
  label: string;
  quantity: number;
}

export interface GuestAmenityRequestDto {
  booking_id: string;
  items: GuestAmenityRequestItem[];
}

export interface GuestAmenityChargeItem {
  label: string;
  quantity: number;
  unit_price?: number;
  amount: number;
  free: boolean;
  charge_id?: string;
}

export interface GuestAmenityRequestResponseDto {
  ok: boolean;
  charges_created: number;
  total: number;
  items: GuestAmenityChargeItem[];
}
