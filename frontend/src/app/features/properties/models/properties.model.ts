export interface PropertyListItem {
  propId: number;
  displayName: string;
  countryDisplayName: string;
  location: string;
  starsLabel: string;
  reviewScoreLabel: string;
  yieldScore: number;
  status: string;
  syncStatus: string;
  syncLatencyMs: number;
  unitCount: number;
  manualOverride: boolean;
  profileBadge: string;
  operationalScore: number;
  operationalChecks: Array<{ label: string; ready: boolean }>;
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
  hotelName: string;
  countryDisplayName: string;
  manualOverride: boolean;
  profileBadge: string;
  originalGeneratedName: string;
  operationalScore: number;
  operationalChecks: Array<{ label: string; ready: boolean }>;
  heroMetrics: Array<{ label: string; value: string; detail: string }>;
  profileFacts: Array<{ label: string; value: string }>;
  masterFacts: Array<{ label: string; value: string }>;
}

export interface DashboardQuickStats {
  occupancyRate: number;
  occupancyTrend: number | null;
  totalRevenueMtd: number;
  revenueTrend: number;
  pendingCheckins: number;
  dataHealthScore: number | null;
}

export interface DashboardRevenuePoint {
  period: string;
  revenue: number;
}

export interface DashboardArrival {
  guestName: string;
  initials: string;
  roomType: string;
  nights: number;
  arrivalTime: string;
  statusTag: string;
}

export interface PropertiesDashboardViewModel {
  quickStats: DashboardQuickStats;
  revenueChart: DashboardRevenuePoint[];
  arrivalsToday: DashboardArrival[];
  properties: PropertiesListViewModel;
}

export interface EditPropertyViewModel {
  propId: number;
  hotelName: string;
  displayName: string;
  countryDisplayName: string;
  originalGeneratedName: string;
  manualOverride: boolean;
  nameSource: string;
  profileBadge: string;
  updatedBy: string;
  updatedAt: string;
  description: string;
  highlights: string;
  policies: {
    checkInTime: string;
    checkOutTime: string;
    cancellationPolicy: string;
    petPolicy: string;
    childrenPolicy: string;
    extraBedPolicy: string;
    paymentPolicy: string;
    houseRules: string;
  };
  images: Array<{
    imageUrl: string;
    title: string;
  }>;
  amenities: string[];
  amenityCatalog: Array<{ category: string; items: Array<{ label: string; active: boolean }> }>;
}
