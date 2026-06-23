import type {
  HotelSearchResponseDto,
  HotelSearchResultDto,
  OwnershipCreateResponseDto,
  OwnershipHotelDto,
  OwnershipRoleDto,
  OwnershipUpdateHotelsResponseDto,
  OwnershipUserDetailDto,
  OwnershipUserDetailResponseDto,
  OwnershipUserDto,
  OwnershipUsersResponseDto
} from '../models/ownership.dto';
import type {
  HotelSearchResult,
  HotelSearchViewModel,
  OwnershipHotel,
  OwnershipListViewModel,
  OwnershipRole,
  OwnershipUserDetail,
  OwnershipUserListItem
} from '../models/ownership.model';

function formatDate(value: string | null): string {
  if (!value) return 'N/D';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('es-EC', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function mapUser(dto: OwnershipUserDto): OwnershipUserListItem {
  return {
    userId: dto.user_id,
    username: dto.username,
    email: dto.email,
    displayName: dto.display_name,
    primaryRole: dto.primary_role,
    isActive: dto.is_active,
    hotelCount: dto.hotel_count,
    hotelPreview: dto.hotel_preview,
    hotelOverflow: dto.hotel_overflow,
    createdAtLabel: formatDate(dto.created_at)
  };
}

function mapRole(dto: OwnershipRoleDto): OwnershipRole {
  return { roleName: dto.role_name, description: dto.description };
}

function mapHotel(dto: OwnershipHotelDto): OwnershipHotel {
  return { propId: dto.prop_id, label: dto.label, countryId: dto.country_id ?? null };
}

function mapUserDetail(dto: OwnershipUserDetailDto): OwnershipUserDetail {
  return {
    userId: dto.user_id,
    username: dto.username,
    email: dto.email,
    displayName: dto.display_name,
    primaryRole: dto.primary_role,
    isActive: dto.is_active,
    assignedHotels: dto.assigned_hotels,
    hotels: dto.hotels.map(mapHotel),
    createdAtLabel: formatDate(dto.created_at)
  };
}

function mapSearchResult(dto: HotelSearchResultDto): HotelSearchResult {
  return {
    propId: dto.prop_id,
    label: dto.label,
    hotelName: dto.hotel_name,
    displayName: dto.display_name,
    starRating: dto.star_rating,
    countryId: dto.country_id,
    countryLabel: dto.country_label
  };
}

export function mapOwnershipUsersResponse(dto: OwnershipUsersResponseDto): OwnershipListViewModel {
  return {
    users: dto.users.map(mapUser),
    roles: dto.roles.map(mapRole)
  };
}

export function mapOwnershipUserDetailResponse(dto: OwnershipUserDetailResponseDto): OwnershipUserDetail {
  return mapUserDetail(dto.user);
}

export function mapCreateUserResponse(dto: OwnershipCreateResponseDto) {
  return {
    ok: dto.ok,
    message: dto.message,
    user: dto.user ? mapUserDetail(dto.user) : undefined
  };
}

export function mapUpdateHotelsResponse(dto: OwnershipUpdateHotelsResponseDto) {
  return {
    ok: dto.ok,
    message: dto.message,
    hotels: dto.hotels.map(mapHotel)
  };
}

export function mapHotelSearchResponse(dto: HotelSearchResponseDto): HotelSearchViewModel {
  return {
    items: dto.items.map(mapSearchResult),
    total: dto.total,
    page: dto.page,
    totalPages: dto.total_pages,
    hasNext: dto.has_next,
    hasPrev: dto.has_prev
  };
}
