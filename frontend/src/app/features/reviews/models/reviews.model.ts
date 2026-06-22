export interface ReviewsListViewModel {
  items: ReviewListItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface ReviewListItem {
  id: string;
  bookingId: string;
  propId: number;
  userName: string;
  rating: number;
  title: string;
  comment: string;
  moderationStatus: string;
  staffResponse: string | null;
  createdAt: string;
}

export interface ReviewDetailViewModel {
  id: string;
  bookingId: string;
  propId: number;
  userId: string;
  userName: string;
  rating: number;
  title: string;
  comment: string;
  moderationStatus: string;
  staffResponse: string | null;
  staffResponseAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReviewModerateInput {
  status: string;
  reason: string;
}

export interface ReviewRespondInput {
  response: string;
}
