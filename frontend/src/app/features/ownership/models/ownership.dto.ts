export interface OwnershipUserDto {
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  primary_role_id?: string;
  primary_role: string;
  is_active: boolean;
  assigned_hotels: number[];
  hotel_count: number;
  hotel_preview: string[];
  hotel_overflow: number;
  created_at: string | null;
}

export interface OwnershipRoleDto {
  role_name: string;
  description: string;
}

export interface OwnershipUsersResponseDto {
  users: OwnershipUserDto[];
  roles: OwnershipRoleDto[];
}

export interface OwnershipUserDetailResponseDto {
  user: OwnershipUserDetailDto;
}

export interface OwnershipUserDetailDto {
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  primary_role_id?: string;
  primary_role: string;
  is_active: boolean;
  assigned_hotels: number[];
  hotels: OwnershipHotelDto[];
  created_at: string | null;
}

export interface OwnershipHotelDto {
  prop_id: number;
  label: string;
  country_id?: string | null;
}

export interface OwnershipCreateResponseDto {
  ok: boolean;
  message: string;
  user?: OwnershipUserDetailDto;
}

export interface OwnershipUpdateHotelsResponseDto {
  ok: boolean;
  message: string;
  hotels: OwnershipHotelDto[];
}

export interface HotelSearchResultDto {
  prop_id: number;
  label: string;
  hotel_name?: string;
  display_name?: string;
  star_rating?: number;
  country_id?: string;
  country_label?: string;
}

export interface HotelSearchResponseDto {
  items: HotelSearchResultDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
