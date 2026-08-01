/**
 * Wire-shape DTO shared by `/api/hotels/availability` and the legacy
 * `/api/hotels/search` endpoint.
 *
 * The customer-facing search uses the operational availability endpoint. The
 * legacy analytics endpoint is still consumed by older callers, so its fields
 * remain optional instead of forcing those callers to lie about the wire
 * shape.
 */
export interface HotelSearchDto {
  items: HotelSearchItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  total_is_estimate?: boolean;
  filters: Record<string, unknown>;
  alternative_destinations?: AlternativeDestinationDto[];
}

export interface AlternativeDestinationDto {
  id: number;
  display_name: string;
}

export interface HotelSearchItemDto {
  prop_id: number;

  // Operational availability fields.
  hotel_name?: string | null;
  display_name?: string | null;
  image_url?: string | null;
  prop_starrating?: number | null;
  prop_review_score?: number | null;
  destination_labels?: string[];
  general_amenities?: string[];
  available_room_types_count?: number | null;
  matched_room_type?: {
    room_type_id: string;
    name: string;
    max_adults: number;
    max_children: number;
    base_capacity: number;
  } | null;
  min_nightly_rate?: number | null;
  min_nightly_rate_label?: string | null;
  total_estimated?: number | null;
  total_estimated_label?: string | null;

  // Legacy analytics aliases. They are optional because availability does not
  // return historical fact metrics.
  hotel_label?: string | null;
  hotel_display_label?: string | null;
  min_price?: number | null;
  gross_revenue?: number | null;
  gross_revenue_label?: string | null;
}
