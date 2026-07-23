export interface ReviewsListViewModel {
  items: ReviewListItem[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
}

export interface ServiceRatings {
  housekeeping?: number | null;
  foodBeverage?: number | null;
  staff?: number | null;
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
  sentimentLabel: string | null;
  sentimentScore: number | null;
  serviceRatings?: ServiceRatings | null;
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
  sentimentLabel: string | null;
  sentimentScore: number | null;
  sentimentConfidence: number | null;
  sentimentAnalyzedAt: string | null;
  serviceRatings?: ServiceRatings | null;
  createdAt: string;
  updatedAt: string;
}

export interface ReputationDashboard {
  gri: number;
  griTarget: number;
  griChange: number;
  totalReviews: number;
  departmental: DepartmentalSentiment[];
  recentFeedback: RecentFeedbackItem[];
  dailyCounts: DailyCount[];
}

export interface DepartmentalSentiment {
  key: string;
  label: string;
  icon: string;
  score: number;
  positivePct: number;
  neutralPct: number;
  negativePct: number;
  totalRatings: number;
}

export interface RecentFeedbackItem {
  id: string;
  userName: string;
  rating: number;
  comment: string;
  createdAt: string;
}

export interface DailyCount {
  date: string;
  count: number;
}
