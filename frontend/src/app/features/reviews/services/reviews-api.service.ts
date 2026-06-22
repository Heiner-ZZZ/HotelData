import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapReviewDetail, mapReviewsList } from '../mappers/reviews.mapper';
import type { ReviewDetailDto, ReviewsListDto } from '../models/reviews.dto';

@Injectable({ providedIn: 'root' })
export class ReviewsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getReviews(page: number, moderationStatus?: string) {
    let params = new HttpParams().set('page', String(page));
    if (moderationStatus) params = params.set('moderation_status', moderationStatus);
    return this.http
      .get<ReviewsListDto>(`${this.apiConfig.baseUrl}/reviews`, { params, withCredentials: true })
      .pipe(map(dto => mapReviewsList(dto)));
  }

  getReviewDetail(reviewId: string) {
    return this.http
      .get<ReviewDetailDto>(`${this.apiConfig.baseUrl}/reviews/${reviewId}`, { withCredentials: true })
      .pipe(map(dto => mapReviewDetail(dto)));
  }

  moderateReview(reviewId: string, status: string, reason: string) {
    return this.http.patch<ReviewDetailDto>(
      `${this.apiConfig.baseUrl}/reviews/${reviewId}/moderate`,
      { status, reason },
      { withCredentials: true },
    );
  }

  respondToReview(reviewId: string, response: string) {
    return this.http.patch<ReviewDetailDto>(
      `${this.apiConfig.baseUrl}/reviews/${reviewId}/respond`,
      { response },
      { withCredentials: true },
    );
  }
}
