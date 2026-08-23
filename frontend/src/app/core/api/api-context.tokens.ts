import { HttpContextToken } from '@angular/common/http';

/**
 * Skip the base URL prefix interceptor.
 * Use for external API calls that shouldn't get '/api' prepended.
 *
 * Usage:
 *   this.http.get('https://external.api/maps', {
 *     context: new HttpContext().set(BYPASS_BASE_URL, true)
 *   });
 */
export const BYPASS_BASE_URL = new HttpContextToken<boolean>(() => false);

/**
 * Skip the global red toast for this request.
 *
 * Use for flows that already report their own errors in a single summary
 * toast (e.g. bulk check-in / bulk confirm): the interceptor's per-request
 * red toast would otherwise duplicate the same message once per failed row.
 * The error is STILL converted to a typed `ApiError` and re-thrown — only
 * the automatic toast is suppressed.
 *
 * Usage:
 *   this.http.post('/api/foo', body, {
 *     context: new HttpContext().set(SUPPRESS_ERROR_TOAST, true)
 *   });
 */
export const SUPPRESS_ERROR_TOAST = new HttpContextToken<boolean>(() => false);
