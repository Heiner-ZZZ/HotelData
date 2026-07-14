import { HttpInterceptorFn } from '@angular/common/http';

import { BYPASS_BASE_URL } from './api-context.tokens';

const API_PREFIX = '/api';

/**
 * Auto-prepends `/api` to relative request URLs so services can write
 * clean paths like `/bookings` instead of `${baseUrl}/bookings`.
 *
 * Skips absolute URLs (`http://…`, `https://…`) and requests marked
 * with `BYPASS_BASE_URL` context token.
 *
 * Must be placed **before** `authInterceptor` in the interceptor chain
 * so the auth interceptor sees the full `/api/…` URL for credential detection.
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.context.get(BYPASS_BASE_URL)) {
    return next(req);
  }

  const url = req.url;

  // Skip absolute URLs (external APIs)
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('//')) {
    return next(req);
  }

  // Skip if already prefixed (direct calls or already-processed requests)
  if (url.startsWith(API_PREFIX)) {
    return next(req);
  }

  const prefixed = req.clone({ url: `${API_PREFIX}${url.startsWith('/') ? url : `/${url}`}` });
  return next(prefixed);
};
