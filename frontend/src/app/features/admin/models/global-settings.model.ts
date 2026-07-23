export interface PlatformConfig {
  defaultCommissionPct: number;
  defaultIvaPct: number;
  updatedAt: string | null;
  updatedBy: string | null;
}

export interface HotelGlobalItem {
  propId: number;
  hotelName: string;
  displayName: string;
  countryName: string;
  city: string;
  province: string;
  hotelGroup: string;
  propCountryId: number | string | null;
}

export interface HotelGlobalList {
  items: HotelGlobalItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface TaxRate {
  countryId: number;
  countryName: string;
  ivaPct: number;
  updatedAt: string;
}

export interface CommissionRate {
  propId: number;
  hotelName: string;
  commissionPct: number;
  updatedAt: string;
}
