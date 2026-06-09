export interface HotelSearchFilters {
  destination: string;
  minPrice: string;
  maxPrice: string;
  minStars: string;
  promotion: '' | 'yes' | 'no';
  adults: string;
  children: string;
  rooms: string;
  page: number;
}

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

export interface HotelSearchPageData {
  items: HotelSearchResult[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
  sourceCollection: string;
  filters: HotelSearchFilters;
  startIndex: number;
  endIndex: number;
}
