export interface RoomsViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  manualOverride: boolean;
  profileBadge: string;
  avgPriceLabel: string;
  sourceCollection: string;
  totalRoomTypes: number;
  totalHotelRooms: number;
  roomTypes: RoomTypeItem[];
  hotelRooms: HotelRoomItem[];
}

export interface RoomFeatureItem {
  label: string;
  unitPrice: number;
}

export interface RoomTypeItem {
  id: string;
  name: string;
  description: string;
  capacityLabel: string;
  activeLabel: string;
  roomNumber: string;
  floor: string;
  features: RoomFeatureItem[];
  baseRate?: number;
}

export interface RoomFeature {
  label: string;
  category: string;
  icon: string;
  custom: boolean;
  source?: string;
  unitPrice?: number;
}

export interface FeatureCategory {
  category: string;
  items: RoomFeature[];
}

export interface UpcomingBooking {
  guest_name: string;
  check_in: string;
  check_out: string;
  status: string;
}

export interface HotelRoomItem {
  id: string;
  roomTypeName: string;
  roomLabel: string;
  activeLabel: string;
  roomNumber: string;
  floor: string;
  upcomingBookings?: UpcomingBooking[];
  isOccupiedSoon?: boolean;
  occupancyLabel?: string;
}

export interface RoomPropertyOption {
  propId: number;
  label: string;
}
