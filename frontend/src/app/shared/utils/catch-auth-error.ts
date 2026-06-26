import { HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

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
        if (err instanceof HttpErrorResponse && err.status === 401) {
          const augmented = err as HttpErrorResponse & { authRequired: boolean };
          augmented.authRequired = true;
          return throwError(() => augmented);
        }
        return throwError(() => err);
      }),
    );
}
