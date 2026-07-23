export interface PlatformConfigDto {
  default_commission_pct: number;
  default_iva_pct: number;
  updated_at: string | null;
  updated_by: string | null;
}

export interface HotelGlobalItemDto {
  prop_id: number;
  hotel_name: string;
  display_name: string;
  country_name: string;
  city: string;
  province: string;
  hotel_group: string;
  prop_country_id: number | string | null;
  prop_starrating?: number | null;
}

export interface HotelGlobalListDto {
  items: HotelGlobalItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TaxRateDto {
  country_id: number;
  country_name: string;
  iva_pct: number;
  updated_at: string;
}

export interface CommissionRateDto {
  prop_id: number;
  hotel_name: string;
  commission_pct: number;
  updated_at: string;
}
