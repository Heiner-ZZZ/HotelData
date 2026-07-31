/**
 * Wire-shape DTO for `/api/hotels/search`.
 *
 * HONEST MAPPING: This DTO reflects what the endpoint ACTUALLY returns on the
 * wire today (analytics-fact rows from MongoDB), NOT what the customer-facing
 * hotel-detail CRUD module exposes. The earlier shape assumed the search
 * endpoint mirrored the CRUD module's per-hotel envelope — but that contract
 * was never true and resulted in silent `undefined` reads (no hotel name,
 * same loremflickr image for everyone). The mapper's per-field drift audit
 * (see `mappers/hotel-search.mapper.ts:mapHotelSearchItems`) is the SINGLE
 * source of truth for catching any future re-inflation of those fields.
 *
 * Wire key examples (curled live from FastAPI 2026-07-30):
 *   `_id`, `prop_id`, `events`, `reservations`, `clicks`, `promotions`,
 *   `avg_price`, `min_price`, `max_price`, `gross_revenue`,
 *   `prop_starrating`, `prop_review_score`, `prop_country_id`,
 *   `geo_country_code`, `destinations`, `hotel_label`,
 *   `hotel_display_label`, `country_display_name`, `destination_labels`,
 *   `avg_price_label`, `gross_revenue_label`, `review_label`,
 *   `conversion_rate`, `click_rate`, `has_promotion`.
 */
export interface HotelSearchDto {
  items: HotelSearchItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
  filters: Record<string, unknown>;
  alternative_destinations?: AlternativeDestinationDto[];
}

export interface AlternativeDestinationDto {
  id: number;
  display_name: string;
}

export interface HotelSearchItemDto {
  prop_id: number;
  // Front-end-visible canonical fields. All nullable because the analytics
  // pipeline that backs /api/hotels/search has occasionally dropped any of
  // these — the mapper audit logs the SCOPE of drift instead of silently
  // substituting a fallback string. Card template handles null gracefully.
  hotel_label: string | null;
  hotel_display_label: string | null;
  prop_starrating: number | null;
  prop_review_score: number | null;
  destination_labels: string[];
  // [FIX BUG] tracked-but-not-rendered: the three price fields below are
  // present on the wire (analytics-fact endpoint returns them on /api/hotels/search)
  // but the mapper (`mappers/hotel-search.mapper.ts`) deliberately nulls
  // them out in HotelSearchResult. Reasons: `min_price` is the historical
  // smallest sale price across all bookings, `gross_revenue` is cumulative
  // revenue across all bookings — neither matches the live-rate UI promise
  // of "<card chip> Desde $X / Total estimado $Y". Showing them as live
  // pricing misled guests (the actual booking cost differs). Live rates live
  // on the hotel-detail page via a separate endpoint.
  //
  // They are STILL audited via the `wire_only_*` counters in the mapper's
  // per-field drift audit so a backend regression that drops them entirely
  // surfaces in console. A non-null wire value does NOT count as "missing"
  // since we deliberately null them out downstream.
  min_price: number | null;
  gross_revenue: number | null;
  gross_revenue_label: string | null;
}
