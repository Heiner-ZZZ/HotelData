export interface PropertyListItem {
  propId: number;
  displayName: string;
  countryDisplayName: string;
  starsLabel: string;
  reviewScoreLabel: string;
  performance: {
    searches: number;
    clicks: number;
    reservations: number;
    grossRevenueLabel: string;
  };
}

export interface PropertiesListViewModel {
  items: PropertyListItem[];
  query: string;
  page: number;
  totalPages: number;
  total: number;
  startIndex: number;
  endIndex: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface PropertyDetailViewModel {
  propId: number;
  displayName: string;
  heroMetrics: Array<{ label: string; value: string; detail: string }>;
  profileFacts: Array<{ label: string; value: string }>;
  masterFacts: Array<{ label: string; value: string }>;
}
