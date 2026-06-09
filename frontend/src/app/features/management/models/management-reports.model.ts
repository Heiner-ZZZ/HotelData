export interface ManagementReportsViewModel {
  sourceCollection: string;
  totalEvents: number;
  reservationsDetected: number;
  grossRevenueLabel: string;
  topHotels: Array<{
    propId: number;
    displayName: string;
    profileBadge: string;
    grossRevenueLabel: string;
    events: number;
  }>;
  topDestinations: Array<{
    label: string;
    events: number;
    grossRevenueLabel: string;
  }>;
  topVisitorCountries: Array<{
    label: string;
    events: number;
    reservations: number;
  }>;
  operationalCounts: Array<{
    label: string;
    value: number;
  }>;
}
