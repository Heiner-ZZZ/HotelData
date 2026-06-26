export interface HotelProductDto {
  product_id: string;
  prop_id: number;
  name: string;
  description: string;
  unit_price: number;
  quantity_available: number;
  category: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface HotelProductListDto {
  items: HotelProductDto[];
}

export interface BookingLineItemDto {
  item_id: string;
  product_id: string;
  name: string;
  quantity: number;
  unit_price: number;
  total: number;
  added_at: string;
  added_by: string;
}

export interface BookingLineItemListDto {
  items: BookingLineItemDto[];
}

export interface AddLineItemPayload {
  product_id: string;
  name: string;
  unit_price: number;
  quantity: number;
}

export interface RemoveLineItemResponse {
  ok: boolean;
}
