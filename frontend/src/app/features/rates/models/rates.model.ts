export interface RatesViewModel {
  propId: number;
  hotelLabel: string;
  manualOverride: boolean;
  profileBadge: string;
  roomTypes: Array<{ id: string; name: string }>;
  ratePlans: RatePlanItem[];
  calendar: RateCalendarItem[];
  rateRules: Array<{ label: string; detail: string }>;
  seasonalRules: SeasonalRuleItem[];
  promotions: Array<{
    campaignId: string;
    name: string;
    description: string;
    discountPercent: number;
    dateRange: string;
    activeLabel: string;
  }>;
  coupons: Array<{ code: string; activeLabel: string }>;
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
  activeLabel: string;
}

export interface RateCalendarItem {
  date: string;
  planName: string;
  rateAmountLabel: string;
  minStayNights: number;
  closedLabel: string;
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
