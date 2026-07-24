export interface OwnershipUserListItem {
  userId: string;
  username: string;
  email: string;
  displayName: string;
  primaryRole: string;
  primaryRoleId: string;
  isActive: boolean;
  hotelCount: number;
  hotelPreview: string[];
  hotelOverflow: number;
  createdAtLabel: string;
}

export interface OwnershipRole {
  roleName: string;
  description: string;
}

export interface OwnershipListViewModel {
  users: OwnershipUserListItem[];
  roles: OwnershipRole[];
}

export interface OwnershipHotel {
  propId: number;
  label: string;
  countryId: string | null;
}

export interface OwnershipUserDetail {
  userId: string;
  username: string;
  email: string;
  displayName: string;
  primaryRole: string;
  primaryRoleId: string;
  isActive: boolean;
  assignedHotels: number[];
  hotels: OwnershipHotel[];
  createdAtLabel: string;
}

export interface HotelSearchResult {
  propId: number;
  label: string;
  hotelName?: string;
  displayName?: string;
  starRating?: number;
  countryId?: string;
  countryLabel?: string;
}

export interface HotelSearchViewModel {
  items: HotelSearchResult[];
  total: number;
  page: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}
