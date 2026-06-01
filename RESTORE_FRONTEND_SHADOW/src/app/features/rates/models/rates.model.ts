export interface RatesPropertyOption {
  propId: number;
  label: string;
}

export interface RatePlanItem {
  ratePlanId: string;
  name: string;
  description: string;
  baseRateLabel: string;
  currency: string;
  isActive: boolean;
}

export interface RateCalendarItem {
  date: string;
  ratePlanId: string;
  planName: string;
  rateAmountLabel: string;
  minStayNights: number | null;
  isClosed: boolean;
}

export interface RatesPageViewModel {
  property: {
    propId: number;
    hotelLabel: string;
  };
  options: {
    properties: RatesPropertyOption[];
    ratePlans: Array<{ ratePlanId: string; name: string; baseRateLabel: string; currency: string }>;
  };
  ratePlans: RatePlanItem[];
  calendar: RateCalendarItem[];
  summary: {
    totalRatePlans: number;
    activeRatePlans: number;
    calendarRows: number;
    closedDates: number;
  };
}
