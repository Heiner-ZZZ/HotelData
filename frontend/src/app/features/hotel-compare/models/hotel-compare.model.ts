export interface PolicyItem {
  label: string;
  value: string;
}

export interface HotelCompareItem {
  propId: number;
  hotelName: string;
  displayName: string;
  propStarrating: number | null;
  propReviewScore: number | null;
  imageUrl: string | null;
  amenitiesText: string;
  roomTypes: HotelCompareRoomType[];
  policies: Record<string, unknown>;
  mappedPolicies: PolicyItem[];
  cancellationPolicy: string;
  destinationLabels: string[];
  latitude: number;
  longitude: number;
  minNightlyRate?: number;
  minNightlyRateLabel?: string;
  totalEstimated?: number;
  totalEstimatedLabel?: string;
}

export interface HotelCompareRoomType {
  roomTypeId: string;
  name: string;
  maxAdults: number;
  maxChildren: number;
  baseCapacity: number;
  description?: string;
}

/** Per-hotel flags showing which attributes are better than the comparison average. */
export interface ComparisonFlags {
  betterPrice: boolean;
  betterScore: boolean;
  betterStars: boolean;
  betterRoomTypes: boolean;
}

export interface HotelCompareData {
  items: HotelCompareItem[];
}
