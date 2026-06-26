export interface Destination {
  srchDestinationId: number;
  destinationDisplayName: string;
  destinationName: string;
  visibleName: string;
  country: string;
  city: string;
  description: string;
  latitude: number | null;
  longitude: number | null;
  destinationRegionLabel: string;
  active: boolean;
}

export interface PaginatedDestinations {
  items: Destination[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface GeoDestination {
  srchDestinationId: number;
  destinationDisplayName: string;
  visibleName: string;
  country: string;
  city: string;
  latitude: number | null;
  longitude: number | null;
}

export interface GeoHotel {
  propId: number;
  hotelName: string;
  displayName: string;
  stars: number | null;
  reviewScore: number | null;
  latitude: number | null;
  longitude: number | null;
  srchDestinationId: number | null;
  destinationDisplayName: string;
}
