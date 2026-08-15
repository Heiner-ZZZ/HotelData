import { HttpErrorResponse } from '@angular/common/http';

/** Conflicto «el código ya existe en otra campaña de Tarifas» — reportado
 *  por el backend (400 ``COUPON_CODE_EXISTS`` con ``detail`` estructurado)
 *  o detectado proactivamente contra las options del hotel (marketing). */
export interface CouponConflict {
  /** Código de cupón conflictivo (``coupon_code`` del backend). */
  code: string;
  /** Id de la campaña dueña del código — permite vincularla/preseleccionarla. */
  campaign_id: string;
  campaign_name: string;
  /** Mensaje legible para el banner (el backend lo compone con campaña dueña). */
  message: string;
}

/**
 * Extrae el conflicto estructurado (``code == "COUPON_CODE_EXISTS"``) de
 * cualquier forma de error sin parsear texto:
 * - el `ApiError` plano del interceptor (su `details` conserva el body
 *   `{ detail: {...} }` del backend);
 * - un `HttpErrorResponse` crudo (tests con `HttpTestingController`).
 * Devuelve `null` si el error no es un conflicto de código.
 */
export function parseCouponConflict(err: unknown): CouponConflict | null {
  const httpBody =
    err instanceof HttpErrorResponse ? (err.error as { detail?: unknown } | null) : null;
  const apiDetails =
    !httpBody && err && typeof err === 'object'
      ? (err as { details?: unknown }).details
      : null;
  const detail =
    httpBody?.detail ??
    (apiDetails && typeof apiDetails === 'object'
      ? (apiDetails as { detail?: unknown }).detail
      : null);
  if (!detail || typeof detail !== 'object') return null;
  const d = detail as {
    code?: unknown;
    campaign_id?: unknown;
    campaign_name?: unknown;
    message?: unknown;
    coupon_code?: unknown;
  };
  if (d.code !== 'COUPON_CODE_EXISTS' || typeof d.campaign_id !== 'string' || !d.campaign_id) {
    return null;
  }
  return {
    code:
      typeof d.coupon_code === 'string' && d.coupon_code
        ? d.coupon_code
        : typeof d.code === 'string'
          ? d.code
          : '',
    campaign_id: d.campaign_id,
    campaign_name: typeof d.campaign_name === 'string' ? d.campaign_name : '',
    message: typeof d.message === 'string' ? d.message : '',
  };
}
