export interface HotelSearchDto {
  items: Array<{
    prop_id: number;
    hotel_label: string;
    country_display_name: string;
    prop_starrating: number | null;
    review_label: string;
    has_promotion: boolean;
    avg_price_label: string;
    reservations: number;
    clicks: number;
    conversion_rate: number;
    destination_labels: string[];
  }>;
}
