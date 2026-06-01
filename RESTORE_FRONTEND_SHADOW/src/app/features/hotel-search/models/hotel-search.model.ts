export interface HotelSearchResult {
  id: number;
  name: string;
  location: string;
  stars: number | null;
  reviewLabel: string;
  hasPromotion: boolean;
  avgPriceLabel: string;
  reservations: number;
  clicks: number;
  conversionRate: number;
  destinationLabels: string[];
}

export interface HotelSearchFilters {
  destination: string;
  minPrice: string;
  maxPrice: string;
  minStars: string;
  promotion: string;
  adults: string;
  children: string;
  rooms: string;
}

export interface HotelSearchViewModel {
  items: HotelSearchResult[];
  total: number;
  page: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
  sourceCollection: string;
  startIndex: number;
  endIndex: number;
  filters: HotelSearchFilters;
}
