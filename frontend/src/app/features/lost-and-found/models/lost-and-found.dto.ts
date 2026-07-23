export interface LostItemCreateDto {
  prop_id: number;
  booking_id?: string;
  guest_name?: string;
  guest_contact?: string;
  item_name: string;
  description?: string;
  found_location?: string;
  found_by?: string;
  status?: string;
  notes?: string;
}

export interface LostItemResponseDto {
  id: string;
  prop_id: number;
  booking_id: string;
  guest_name: string;
  guest_contact: string;
  item_name: string;
  description: string;
  found_location: string;
  found_by: string;
  status: string;
  notes: string;
  returned_to: string;
  returned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
