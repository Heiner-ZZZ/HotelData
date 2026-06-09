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
}

export interface HotelRoomItem {
  id: string;
  roomTypeName: string;
  roomLabel: string;
  activeLabel: string;
}

export interface RoomPropertyOption {
  propId: number;
  label: string;
}
