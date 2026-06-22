import { Routes } from '@angular/router';

export const REVIEWS_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/reviews-list-page/reviews-list-page').then(m => m.ReviewsListPageComponent),
  },
  {
    path: ':reviewId',
    loadComponent: () =>
      import('./pages/review-detail-page/review-detail-page').then(m => m.ReviewDetailPageComponent),
  },
];
