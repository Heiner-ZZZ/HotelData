import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { ToastService } from '../../shared/services/toast.service';
import { SUPPRESS_ERROR_TOAST } from './api-context.tokens';
import type { ApiError } from './api-error.model';

/**
 * Universal HTTP error boundary. Two responsibilities:
 *   1. Convert every HttpErrorResponse into a typed `ApiError` with a
 *      readable `message` (used by the existing 68 catch sites and any
 *      `error: (err: ApiError) => ...` handlers downstream).
 *   2. Fire a red toast so the failure is visible at the top of the
 *      viewport. This is the safety-net for the 68 silent `.catch()` /
 *      `error: () => ...` sites that previously hid errors from both
 *      dev and user — even if a calling catch swallows the err
 *      afterwards, the global toast already announced it.
 *
 * Opt-out: requests marked with {@link SUPPRESS_ERROR_TOAST} skip the
 * automatic toast (the caller reports its own summary), but still get the
 * typed `ApiError`.
 */
export const httpErrorInterceptor: HttpInterceptorFn = (request, next) => {
  const toast = inject(ToastService);
  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const detail = error.error?.detail;
        const message =
          error.error?.message ||
          (typeof detail === 'string'
            ? detail
            : detail?.detail ?? detail?.message) ||
          error.message ||
          'Unexpected API error';

        if (!request.context.get(SUPPRESS_ERROR_TOAST)) {
          toast.error(message);
        }

        const apiError: ApiError = {
          status: error.status,
          message,
          details: error.error,
        };
        return throwError(() => apiError);
      }

      return throwError(() => error);
    })
  );
};
