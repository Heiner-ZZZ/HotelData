import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

import type { ApiError } from './api-error.model';

export const httpErrorInterceptor: HttpInterceptorFn = (request, next) =>
  next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const detail = error.error?.detail;
        const apiError: ApiError = {
          status: error.status,
          message:
            error.error?.message ||
            (typeof detail === 'string' ? detail : detail?.detail) ||
            error.message ||
            'Unexpected API error',
          details: error.error
        };
        return throwError(() => apiError);
      }

      return throwError(() => error);
    })
  );
