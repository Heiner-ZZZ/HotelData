import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapReviewDetail, mapReviewsList, mapReputationDashboard } from '../mappers/reviews.mapper';
import type { ReputationDashboardDto, ReviewAnalyticsDto, ReviewDetailDto, ReviewsListDto } from '../models/reviews.dto';
import { mapReviewAnalytics } from '../mappers/reviews.mapper';

@Injectable({ providedIn: 'root' })
export class ReviewsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReviews(page: number, moderationStatus?: string, propId?: number) {
    let params = new HttpParams().set('page', String(page));
    if (moderationStatus) params = params.set('moderation_status', moderationStatus);
    if (propId) params = params.set('prop_id', String(propId));
    return this.http
      .get<ReviewsListDto>(`${this.apiConfig.baseUrl}/reviews`, { params, withCredentials: true })
      .pipe(map(dto => mapReviewsList(dto)));
  }

  getReviewDetail(reviewId: string) {
    return this.http
      .get<ReviewDetailDto>(`${this.apiConfig.baseUrl}/reviews/${reviewId}`, { withCredentials: true })
      .pipe(map(dto => mapReviewDetail(dto)));
  }

  moderateReview(reviewId: string, status: string, reason: string, propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : new HttpParams();
    return this.http.patch<ReviewDetailDto>(
      `${this.apiConfig.baseUrl}/reviews/${reviewId}/moderate`,
      { status, reason },
      { params, withCredentials: true },
    );
  }

  respondToReview(reviewId: string, response: string, propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : new HttpParams();
    return this.http.patch<ReviewDetailDto>(
      `${this.apiConfig.baseUrl}/reviews/${reviewId}/respond`,
      { response },
      { params, withCredentials: true },
    );
  }

  // Create a review with optional service ratings
  createReview(payload: {
    booking_id: string;
    prop_id: number;
    rating: number;
    title?: string;
    comment?: string;
    service_ratings?: {
      housekeeping?: number | null;
      food_beverage?: number | null;
      staff?: number | null;
    };
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/reviews/guest`,
      payload,
      { withCredentials: true },
    );
  }

  // Create a review as staff (on behalf of guest)
  createStaffReview(payload: {
    booking_id: string;
    prop_id: number;
    rating: number;
    title?: string;
    comment?: string;
    service_ratings?: {
      housekeeping?: number | null;
      food_beverage?: number | null;
      staff?: number | null;
    };
  }) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/reviews/staff`,
      payload,
      { withCredentials: true },
    );
  }

  getReputationAnalytics(propId?: number, days = 30) {
    let params = new HttpParams().set('days', String(days));
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<ReviewAnalyticsDto>(
      `${this.apiConfig.baseUrl}/reviews/reputation/analytics`,
      { params, withCredentials: true },
    ).pipe(map(dto => mapReviewAnalytics(dto)));
  }

  // Get reputation dashboard data
  getReputationDashboard(propId?: number, days = 30) {
    let params = new HttpParams().set('days', String(days));
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<ReputationDashboardDto>(
      `${this.apiConfig.baseUrl}/reviews/reputation/dashboard`,
      { params, withCredentials: true },
    ).pipe(map(dto => mapReputationDashboard(dto)));
  }

  // Get approved reviews for a hotel (public, no auth)
  getHotelReviews(propId: number, page = 1, pageSize = 5) {
    const params = new HttpParams()
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http.get<ReviewsListDto>(
      `${this.apiConfig.baseUrl}/hotels/${propId}/reviews`,
      { params },
    );
  }
}
