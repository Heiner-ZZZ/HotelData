export interface ManagementReportsDto {
  source_collection: string;
  total_events: number;
  reservations_detected: number;
  gross_revenue: number;
  top_hotels_by_revenue: Array<{
    prop_id: number;
    display_name: string;
    manual_override: boolean;
    profile_badge: string;
    gross_revenue: number;
    events: number;
  }>;
  top_destinations: Array<{
    srch_destination_id: number;
    label: string;
    events: number;
    gross_revenue: number;
  }>;
  top_visitor_countries: Array<{
    visitor_location_country_id: number;
    label: string;
    events: number;
    reservations: number;
  }>;
  operational_counts: Array<{
    label: string;
    value: number;
  }>;
}
