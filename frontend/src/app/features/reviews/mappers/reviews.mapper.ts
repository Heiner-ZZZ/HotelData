import { formatDateTime } from '../../../shared/utils/date-format.util';
import type { ReviewDetailDto, ReviewItemDto, ReviewsListDto, ServiceRatingsDto } from '../models/reviews.dto';
import type { ReviewDetailViewModel, ReviewListItem, ReviewsListViewModel, ServiceRatings, ReputationDashboard } from '../models/reviews.model';

function mapServiceRatings(sr?: ServiceRatingsDto | null): ServiceRatings | null {
  if (!sr) return null;
  return {
    housekeeping: sr.housekeeping ?? null,
    foodBeverage: sr.food_beverage ?? null,
    staff: sr.staff ?? null,
  };
}

function mapReviewItem(item: ReviewItemDto): ReviewListItem {
  return {
    id: item.id,
    bookingId: item.booking_id,
    propId: item.prop_id,
    userName: item.user_display_name || item.user_id,
    rating: item.rating,
    title: item.title,
    comment: item.comment,
    moderationStatus: item.moderation_status,
    staffResponse: item.staff_response,
    sentimentLabel: item.sentiment_label,
    sentimentScore: item.sentiment_score,
    serviceRatings: mapServiceRatings(item.service_ratings),
    createdAt: formatDateTime(item.created_at),
  };
}

export function mapReviewsList(dto: ReviewsListDto): ReviewsListViewModel {
  return {
    items: dto.items.map(mapReviewItem),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
  };
}

export function mapReviewDetail(dto: ReviewDetailDto): ReviewDetailViewModel {
  return {
    id: dto.id,
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    userId: dto.user_id,
    userName: dto.user_display_name || dto.user_id,
    rating: dto.rating,
    title: dto.title,
    comment: dto.comment,
    moderationStatus: dto.moderation_status,
    staffResponse: dto.staff_response,
    staffResponseAt: dto.staff_response_at,
    sentimentLabel: dto.sentiment_label,
    sentimentScore: dto.sentiment_score,
    sentimentConfidence: dto.sentiment_confidence,
    sentimentAnalyzedAt: dto.sentiment_analyzed_at,
    serviceRatings: mapServiceRatings(dto.service_ratings),
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

/** Map reputation dashboard from API snake_case to camelCase. */
export function mapReputationDashboard(dto: any): ReputationDashboard {
  return {
    gri: dto.gri ?? 0,
    griTarget: dto.gri_target ?? 90,
    griChange: dto.gri_change ?? 0,
    totalReviews: dto.total_reviews ?? 0,
    departmental: (dto.departmental ?? []).map((dept: any) => ({
      key: dept.key,
      label: dept.label,
      icon: dept.icon,
      score: dept.score,
      positivePct: dept.positive_pct ?? 0,
      neutralPct: dept.neutral_pct ?? 0,
      negativePct: dept.negative_pct ?? 0,
      totalRatings: dept.total_ratings ?? 0,
    })),
    recentFeedback: (dto.recent_feedback ?? []).map((fb: any) => ({
      id: fb.id,
      userName: fb.user_name ?? 'Huésped',
      rating: fb.rating ?? 0,
      comment: fb.comment ?? '',
      createdAt: fb.created_at ?? '',
    })),
    dailyCounts: (dto.daily_counts ?? []).map((dc: any) => ({
      date: dc.date,
      count: dc.count ?? 0,
    })),
  };
}
