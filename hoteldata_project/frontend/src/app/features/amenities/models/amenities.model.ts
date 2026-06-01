export interface AmenitiesPropertyOption {
  propId: number;
  label: string;
}

export interface AmenityItemViewModel {
  label: string;
  active: boolean;
}

export interface AmenityCategoryViewModel {
  category: string;
  items: AmenityItemViewModel[];
}

export interface AmenitiesViewModel {
  propId: number;
  hotelName: string;
  countryLabel: string;
  reviewLabel: string;
  avgPriceLabel: string;
  sourceCollection: string;
  activeAmenities: string[];
  categories: AmenityCategoryViewModel[];
}
