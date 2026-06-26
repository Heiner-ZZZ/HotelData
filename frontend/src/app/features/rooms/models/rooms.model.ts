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

export interface RoomTypeItem {
  id: string;
  name: string;
  description: string;
  capacityLabel: string;
  activeLabel: string;
  roomNumber: string;
  floor: string;
  features: string[];
}

export interface RoomFeature {
  label: string;
  category: string;
  icon: string;
  custom: boolean;
}

export interface FeatureCategory {
  category: string;
  items: RoomFeature[];
}

export interface HotelRoomItem {
  id: string;
  roomTypeName: string;
  roomLabel: string;
  activeLabel: string;
  roomNumber: string;
  floor: string;
}

export interface RoomPropertyOption {
  propId: number;
  label: string;
}
