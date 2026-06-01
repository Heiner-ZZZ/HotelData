export interface HotelSearchResult {
  id: number;
  name: string;
  location: string;
  stars: number | null;
  reviewLabel: string;
  hasPromotion: boolean;
  avgPriceLabel: string;
  reservations: number;
  clicks: number;
  conversionRate: number;
  destinationLabels: string[];
}
