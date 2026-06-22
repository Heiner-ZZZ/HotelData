import { formatDateTime } from '../../../shared/utils/date-format.util';
import type { ReviewDetailDto, ReviewItemDto, ReviewsListDto } from '../models/reviews.dto';
import type { ReviewDetailViewModel, ReviewListItem, ReviewsListViewModel } from '../models/reviews.model';

function mapReviewItem(item: ReviewItemDto): ReviewListItem {
  return {
    id: item._id,
    bookingId: item.booking_id,
    propId: item.prop_id,
    userName: item.user_display_name || item.user_id,
    rating: item.rating,
    title: item.title,
    comment: item.comment,
    moderationStatus: item.moderation_status,
    staffResponse: item.staff_response,
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
    id: dto._id,
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
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}
