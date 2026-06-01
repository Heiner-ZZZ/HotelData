export interface AmenitiesDto {
  hotel: {
    prop_id: number;
    display_name: string;
    country_display_name: string;
    review_score_label: string;
  };
  performance: {
    avg_price_label: string;
    source_collection: string;
  };
  amenities: {
    active_amenities: string[];
    catalog: Array<{
      category: string;
      items: Array<{
        label: string;
        active: boolean;
      }>;
    }>;
  };
}

export interface AmenitiesOptionsDto {
  properties: Array<{
    prop_id: number;
    display_name: string;
  }>;
  catalog?: Array<{
    category: string;
    items: Array<{
      label: string;
      active: boolean;
    }>;
  }>;
  active_amenities?: string[];
}

export interface AmenitiesSaveDto {
  prop_id: number;
  active_amenities: string[];
  amenities_text: string;
}
