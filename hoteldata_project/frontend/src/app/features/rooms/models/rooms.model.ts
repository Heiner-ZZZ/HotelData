export interface RoomsViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  sourceCollection: string;
  totalRoomTypes: number;
  roomTypes: RoomTypeItem[];
}

export interface RoomTypeItem {
  id: string;
  name: string;
  description: string;
  capacityLabel: string;
  activeLabel: string;
}

export interface RoomPropertyOption {
  propId: number;
  label: string;
}
