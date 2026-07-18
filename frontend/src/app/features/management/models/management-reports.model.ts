export interface ManagementReportsViewModel {
  sourceCollection: string;
  totalEvents: number;
  reservationsDetected: number;
  grossRevenueLabel: string;
  topHotels: {
    propId: number;
    displayName: string;
    profileBadge: string;
    grossRevenueLabel: string;
    events: number;
  }[];
  topDestinations: {
    label: string;
    events: number;
    grossRevenueLabel: string;
  }[];
  topVisitorCountries: {
    label: string;
    events: number;
    reservations: number;
  }[];
  operationalCounts: {
    label: string;
    value: number;
  }[];
}
