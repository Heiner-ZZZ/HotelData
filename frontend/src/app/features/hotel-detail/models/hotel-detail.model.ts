export interface HotelDetailViewModel {
  id: number;
  name: string;
  location: string;
  starsLabel: string;
  reviewLabel: string;
  averagePrice: string;
  reservations: number;
  clicks: number;
  events: number;
  promotions: number;
  conversionRate: number;
  clickRate: number;
  sourceCollection: string;
  basicFacts: Array<{ label: string; value: string }>;
  topDestinations: Array<{ label: string; events: number; avgPriceLabel: string }>;
  topVisitorCountries: Array<{ id: number; label: string; events: number; reservations: number }>;
  topSites: Array<{ id: number; label: string; events: number; clicks: number; reservations: number }>;
  hotelRates: Array<{ date: string; plan: string; amountLabel: string; minStayLabel: string }>;
  roomTypes: Array<{ id: string; name: string; capacityLabel: string; statusLabel: string }>;
  policies: Array<{ label: string; value: string }>;
  cancellationPolicy: string;
  galleryImages: string[];
  description: string;
  highlights: string;
  amenitiesTags: string[];
  reviews: Array<{
    reviewerName: string;
    score: number;
    text: string;
    date: string;
  }>;
}

export interface SimilarHotel {
  id: number;
  name: string;
  stars: number;
  reviewLabel: string;
  location: string;
  similarityScore: number;
  reason: string;
  imageUrl: string;
}
