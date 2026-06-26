import type {
  PlatformConfigDto,
  HotelGlobalItemDto,
  HotelGlobalListDto,
  TaxRateDto,
  CommissionRateDto,
} from '../models/global-settings.dto';
import type {
  PlatformConfig,
  HotelGlobalItem,
  HotelGlobalList,
  TaxRate,
  CommissionRate,
} from '../models/global-settings.model';

export function mapPlatformConfig(dto: PlatformConfigDto): PlatformConfig {
  return {
    defaultCommissionPct: dto.default_commission_pct,
    defaultIvaPct: dto.default_iva_pct,
    updatedAt: dto.updated_at,
    updatedBy: dto.updated_by,
  };
}

export function mapHotelGlobalItem(dto: HotelGlobalItemDto): HotelGlobalItem {
  return {
    propId: dto.prop_id,
    hotelName: dto.hotel_name,
    displayName: dto.display_name,
    countryName: dto.country_name,
    city: dto.city,
    province: dto.province,
    hotelGroup: dto.hotel_group,
    propCountryId: dto.prop_country_id,
  };
}

export function mapHotelGlobalList(dto: HotelGlobalListDto): HotelGlobalList {
  return {
    items: dto.items.map(mapHotelGlobalItem),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
  };
}

export function mapTaxRate(dto: TaxRateDto): TaxRate {
  return {
    countryId: dto.country_id,
    countryName: dto.country_name,
    ivaPct: dto.iva_pct,
    updatedAt: dto.updated_at,
  };
}

export function mapCommissionRate(dto: CommissionRateDto): CommissionRate {
  return {
    propId: dto.prop_id,
    hotelName: dto.hotel_name,
    commissionPct: dto.commission_pct,
    updatedAt: dto.updated_at,
  };
}
