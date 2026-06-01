export interface RatesViewModel {
  propId: number;
  hotelLabel: string;
  ratePlans: RatePlanItem[];
  calendar: RateCalendarItem[];
}

export interface RatePlanItem {
  id: string;
  name: string;
  description: string;
  baseRateLabel: string;
  currency: string;
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

export interface RatePlanOption {
  id: string;
  label: string;
}
