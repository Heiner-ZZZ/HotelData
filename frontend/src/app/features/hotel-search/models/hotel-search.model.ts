export interface HotelSearchFilters {
  destination: string;
  checkIn: string;
  checkOut: string;
  adults: string;
  children: string;
  rooms: string;
  minPrice: string;
  maxPrice: string;
  minStars: string;
  amenities: string[];
  amenitiesMode: 'or' | 'and';
  sortBy: 'price' | 'rating' | 'stars' | 'name';
  compareIds: number[];
  page: number;
}

export interface HotelSearchResult {
  id: number;
  name: string;
  displayName: string;
  stars: number | null;
  reviewScore: number | null;
  imageUrl: string | null;
  destinationLabels: string[];
  generalAmenities: string[];
  matchedRoomType: {
    roomTypeId: string;
    name: string;
    maxAdults: number;
    maxChildren: number;
    baseCapacity: number;
  } | null;
  minNightlyRate: number | null;
  minNightlyRateLabel: string | null;
  totalEstimated: number | null;
  totalEstimatedLabel: string | null;
  // [FIX BUG] nullable because /api/hotels/search (analytics-fact endpoint)
  // does NOT return `available_room_types_count` — wire-shape drift; mapper
  // logs this in per-field drift audit. Card template's `h.availableRoomTypesCount
  // ? ... : ''` truthy check tolerates null.
  availableRoomTypesCount: number | null;
  selected: boolean;
}

export interface AlternativeDestination {
  id: number;
  displayName: string;
}

export interface HotelSearchPageData {
  items: HotelSearchResult[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  totalIsEstimate: boolean;
  hasPrev: boolean;
  hasNext: boolean;
  filters: HotelSearchFilters;
  // [FIX BUG] Non-optional — `mapHotelSearchResponse` audits missing
  // `alternative_destinations` and substitutes `[]` loudly (`console.error`
  // + dev toast), so callers can trust this is always an array. Without
  // this typed invariant, every consumer must re-introduce `?? []` swallow
  // — the exact regression the user flagged: "tapaste los errores".
  alternativeDestinations: AlternativeDestination[];
}
