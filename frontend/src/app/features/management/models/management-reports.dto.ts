export interface ManagementReportsDto {
  source_collection: string;
  total_events: number;
  reservations_detected: number;
  gross_revenue: number;
  series: {
    labels: string[];
    datasets: { label: string; data: number[] }[];
  };
  rows: {
    month: string;
    events: number;
    reservations: number;
    gross_revenue: number;
  }[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  top_hotels_by_revenue: {
    prop_id: number;
    display_name: string;
    manual_override: boolean;
    profile_badge: string;
    gross_revenue: number;
    events: number;
  }[];
  top_destinations: {
    srch_destination_id: number;
    label: string;
    events: number;
    gross_revenue: number;
  }[];
  top_visitor_countries: {
    visitor_location_country_id: number;
    label: string;
    events: number;
    reservations: number;
  }[];
  operational_counts: {
    label: string;
    value: number;
  }[];
}
