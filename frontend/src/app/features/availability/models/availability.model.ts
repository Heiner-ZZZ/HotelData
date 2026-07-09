export interface AvailabilityViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  minRateLabel: string;
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
  roomTypeId: string;
  roomTypeName: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
  occupancyLabel: string;
  occupancyPct: number;
}

/** A single cell in the visual calendar grid. */
export interface CalendarCell {
  date: string;
  day: number;
  dayName: string;
  isToday: boolean;
  isWeekend: boolean;
  isPast: boolean;
  /** Whether this day falls in the current calendar week (Mon-Sun). */
  isCurrentWeek: boolean;
  /** Aggregated availability info for each room type on this date */
  roomTypes: CalendarRoomTypeCell[];
}

export interface CalendarRoomTypeCell {
  roomTypeId: string;
  roomTypeName: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
  occupancyPct: number;
  /** 0-100 how full the room type is */
}

export interface CalendarMonth {
  year: number;
  month: number;
  monthName: string;
  days: CalendarCell[];
}

export interface AvailabilityBlackoutItem {
  blackoutId?: string;
  roomTypeId: string;
  rangeLabel: string;
  blockedRooms: number;
  reason: string;
  roomNumbers?: string[];
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

/** Individual hotel room info for calendar display. */
export interface HotelRoomInfo {
  hotelRoomId: string;
  roomNumber: string;
  roomLabel: string;
  roomTypeId: string;
  roomTypeName: string;
  floor: string;
  isActive: boolean;
}
