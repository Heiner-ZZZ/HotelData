export interface AmenitiesPropertyOption {
  propId: number;
  label: string;
}

export interface AmenityItemViewModel {
  label: string;
  active: boolean;
  unitPrice?: number;
}

export interface AmenityCategoryViewModel {
  category: string;
  items: AmenityItemViewModel[];
}

export interface RoomTypeOption {
  roomTypeId: string;
  name: string;
  capacityLabel: string;
}

export interface SpecialRequestOptionView {
  label: string;
  unitPrice: number;
  chargeable: boolean;
  petRelated: boolean;
  lateArrival: boolean;
}

export interface AmenitiesViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  sourceCollection: string;
  activeAmenities: string[];
  contentDescription: string;
  imageCount: number;
  facilityCount: number;
  categories: AmenityCategoryViewModel[];
  roomTypes: RoomTypeOption[];
  roomAmenities: Record<string, string[]>;
  specialRequests: SpecialRequestOptionView[];
}
