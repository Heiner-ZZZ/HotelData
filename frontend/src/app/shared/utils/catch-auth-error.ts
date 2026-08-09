import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { getErrorStatus } from './http-error.util';

/**
 * Augments a 401 error with an `authRequired` flag so components can
 * distinguish between session-expired and other errors without having
 * to inspect HTTP status codes themselves.
 *
 * Usage:
 *   getData(): Observable<Data> {
 *     return this.http.get<Data>(url).pipe(catchAuthError());
 *   }
 *
 * The component's `error` callback receives the original error with
 * an additional `authRequired: true` property.
 */
export function catchAuthError<T>() {
  return (source: Observable<T>): Observable<T> =>
    source.pipe(
      catchError((err: unknown) => {
        // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del
        // interceptor (vivo) — el 401 debe marcar authRequired en ambos.
        if (getErrorStatus(err) === 401) {
          (err as { authRequired?: boolean }).authRequired = true;
          return throwError(() => err);
        }
        return throwError(() => err);
      }),
    );
}
