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
