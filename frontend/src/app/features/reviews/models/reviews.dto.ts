export interface ReviewsListDto {
  items: ReviewItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface ServiceRatingsDto {
  housekeeping?: number | null;
  food_beverage?: number | null;
  staff?: number | null;
}

export interface ReviewItemDto {
  id: string;
  booking_id: string;
  prop_id: number;
  user_id: string;
  user_display_name: string;
  rating: number;
  title: string;
  comment: string;
  moderation_status: string;
  staff_response: string | null;
  staff_response_at: string | null;
  sentiment_label: string | null;
  sentiment_score: number | null;
  sentiment_confidence: number | null;
  sentiment_analyzed_at: string | null;
  service_ratings?: ServiceRatingsDto | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewDetailDto {
  id: string;
  booking_id: string;
  prop_id: number;
  user_id: string;
  user_display_name: string;
  rating: number;
  title: string;
  comment: string;
  moderation_status: string;
  staff_response: string | null;
  staff_response_at: string | null;
  sentiment_label: string | null;
  sentiment_score: number | null;
  sentiment_confidence: number | null;
  sentiment_analyzed_at: string | null;
  service_ratings?: ServiceRatingsDto | null;
  created_at: string;
  updated_at: string;
}
