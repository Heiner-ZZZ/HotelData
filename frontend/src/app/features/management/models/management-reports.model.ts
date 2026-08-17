export interface ManagementReportsViewModel {
  sourceCollection: string;
  totalEvents: number;
  reservationsDetected: number;
  grossRevenueLabel: string;
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: {
    month: string;
    events: number;
    reservations: number;
    grossRevenue: number;
    grossRevenueLabel: string;
  }[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
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
