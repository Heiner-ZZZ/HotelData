export interface AvailabilityViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  sourceCollection: string;
  roomTypes: AvailabilityRoomType[];
  inventoryItems: AvailabilityInventoryItem[];
  availabilityBlocks: AvailabilityBlackoutItem[];
  blackoutItems: AvailabilityBlackoutItem[];
}

export interface AvailabilityRoomType {
  id: string;
  name: string;
  capacityLabel: string;
  isActive: boolean;
}

export interface AvailabilityInventoryItem {
  date: string;
  roomTypeName: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
  occupancyLabel: string;
}

export interface AvailabilityBlackoutItem {
  roomTypeId: string;
  rangeLabel: string;
  blockedRooms: number;
  reason: string;
}

export interface AvailabilityPropertyOption {
  propId: number;
  label: string;
}

export interface PropertyOptionsPage {
  items: AvailabilityPropertyOption[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}
