export interface HotelDetailViewModel {
  propId: number;
  hotelLabel: string;
  heroMetrics: Array<{ label: string; value: string; detail: string }>;
  basicFacts: Array<{ label: string; value: string }>;
  topDestinations: Array<{ label: string; events: number; avgPriceLabel: string }>;
  topVisitorCountries: Array<{ label: string; events: number; reservations: number; technicalId: number }>;
  topSites: Array<{ label: string; events: number; clicks: number; reservations: number; technicalId: number }>;
  hotelRates: Array<{ date: string; ratePlanId: string; rateAmountLabel: string; minStayNights: string }>;
  roomTypes: Array<{ name: string; roomTypeId: string; capacityLabel: string; statusLabel: string; isActive: boolean }>;
  policies: Array<{ label: string; value: string }>;
  cancellationPolicy: string;
}
