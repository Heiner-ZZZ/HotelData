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
 * Skip the auth interceptor's `withCredentials` handling.
 * Use for public endpoints or third-party services that don't need session cookies.
 *
 * Usage:
 *   this.http.get('/api/public/rates', {
 *     context: new HttpContext().set(BYPASS_AUTH, true)
 *   });
 */
export const BYPASS_AUTH = new HttpContextToken<boolean>(() => false);
