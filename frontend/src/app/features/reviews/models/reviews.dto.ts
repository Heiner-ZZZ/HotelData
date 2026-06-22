export interface ReviewsListDto {
  items: ReviewItemDto[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_prev: boolean;
  has_next: boolean;
}

export interface ReviewItemDto {
  _id: string;
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
  created_at: string;
  updated_at: string;
}

export interface ReviewDetailDto {
  _id: string;
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
  created_at: string;
  updated_at: string;
}

export interface ReviewModerateDto {
  status: string;
  reason: string;
}

export interface ReviewRespondDto {
  response: string;
}
