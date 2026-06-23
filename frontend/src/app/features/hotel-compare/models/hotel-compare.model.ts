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
  destinationLabels: string[];
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

export interface HotelCompareData {
  items: HotelCompareItem[];
}
