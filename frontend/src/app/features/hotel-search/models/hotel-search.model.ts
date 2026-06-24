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
  availableRoomTypesCount: number;
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
  hasPrev: boolean;
  hasNext: boolean;
  filters: HotelSearchFilters;
  alternativeDestinations?: AlternativeDestination[];
}
