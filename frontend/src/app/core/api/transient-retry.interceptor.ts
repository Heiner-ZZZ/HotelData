import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { retry, throwError, timer } from 'rxjs';

/** Gateway-level errors that mean "upstream is briefly unavailable", not "your request is wrong". */
const TRANSIENT_STATUSES = new Set([502, 503, 504]);
/** Total request attempts (1 original + N retries). */
const MAX_ATTEMPTS = 3;
/** Backoff between attempts (ms). The stack proxies through nginx to a
 *  uvicorn server running with `--reload`; a backend restart leaves a
 *  ~1-3s window of 502s, so the first retry lands right after it. */
const BACKOFF_MS = [500, 1500];

/**
 * Retries idempotent GET requests that fail with a transient gateway
 * error (502/503/504) so the app self-heals across backend restarts
 * (docker compose up, uvicorn --reload). Only GET is safe to retry;
 * every other method and every non-transient status passes through.
 *
 * Must sit AFTER `httpErrorInterceptor` (so retries happen before the
 * error toast fires) and BEFORE `authInterceptor` (so it retries the raw
 * HttpErrorResponse). When retries are exhausted the last error is
 * rethrown untouched and the rest of the chain handles it as usual.
 */
export const transientRetryInterceptor: HttpInterceptorFn = (request, next) => {
  if (request.method !== 'GET') {
    return next(request);
  }

  return next(request).pipe(
    retry({
      count: MAX_ATTEMPTS - 1,
      delay: (error: unknown, attempt: number) => {
        if (error instanceof HttpErrorResponse && TRANSIENT_STATUSES.has(error.status)) {
          const delay = BACKOFF_MS[attempt - 1] ?? BACKOFF_MS[BACKOFF_MS.length - 1];
          return timer(delay);
        }
        return throwError(() => error);
      },
    }),
  );
};
