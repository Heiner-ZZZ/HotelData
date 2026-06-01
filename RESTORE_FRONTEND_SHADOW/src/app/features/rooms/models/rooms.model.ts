export interface RoomsPropertyOption {
  propId: number;
  label: string;
}

export interface RoomTypeItem {
  roomTypeId: string;
  name: string;
  description: string;
  capacityLabel: string;
  maxAdults: number | null;
  maxChildren: number | null;
  baseCapacity: number | null;
  isActive: boolean;
}

export interface RoomsPageViewModel {
  property: {
    propId: number;
    displayName: string;
    countryDisplayName: string;
  };
  options: RoomsPropertyOption[];
  selectedPropId: number | null;
  roomTypes: RoomTypeItem[];
  summary: {
    totalRoomTypes: number;
    activeRoomTypes: number;
    inactiveRoomTypes: number;
  };
}
