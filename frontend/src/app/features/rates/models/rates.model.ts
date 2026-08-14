export interface RatesViewModel {
  propId: number;
  hotelLabel: string;
  manualOverride: boolean;
  profileBadge: string;
  /** Tarifa base mínima (system_config.min_base_rate) para validar el form. */
  minBaseRate: number;
  roomTypes: { id: string; name: string }[];
  ratePlans: RatePlanItem[];
  calendar: RateCalendarItem[];
  rateRules: { label: string; detail: string }[];
  seasonalRules: SeasonalRuleItem[];
  promotions: {
    campaignId: string;
    name: string;
    description: string;
    discountPercent: number;
    dateRange: string;
    activeLabel: string;
  }[];
  coupons: { code: string; activeLabel: string; campaignId: string }[];
  /** Hueco tarifas-vs-inventario para el banner del overview (null = sin hueco). */
  rateCoverage: RateCoverage | null;
}

/** Noches con habitaciones disponibles pero sin tarifa abierta. */
export interface RateCoverage {
  rateLastDate: string | null;
  inventoryLastDate: string;
  gapNights: number;
  gapStart: string;
  gapEnd: string;
}

export interface SeasonalRuleItem {
  ruleId: string;
  name: string;
  ratePlanId: string;
  startDate: string;
  endDate: string;
  priceOverride: number;
  rangeLabel: string;
}

export interface RatePlanItem {
  id: string;
  name: string;
  description: string;
  baseRateLabel: string;
  baseRate: number;
  currency: string;
  roomTypeId?: string;
  applicableRoomTypes?: string[];
  activeLabel: string;
  eligibleRoles?: string[];
  includedAmenities?: string[];
}

export interface RateCalendarItem {
  date: string;
  ratePlanId: string;
  planName: string;
  rateAmount: number;
  rateAmountLabel: string;
  minStayNights: number;
  isClosed: boolean;
  closedLabel: string;
  /** 'generated' = creada por Generar calendario (bulk); '' = editada a mano. */
  source: string;
}

export interface RatePropertyOption {
  propId: number;
  label: string;
}

export interface PropertyOptionsPage {
  items: RatePropertyOption[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

export interface RatePlanOption {
  id: string;
  label: string;
}
