/**
 * Wire shapes de la cola de conciliación del admin
 * (PLAN_SUSCRIPCION_Y_PAGOS.md §6.2).
 *
 * KEEP IN SYNC con `server/src/app/modules/subscriptions/routes_admin.py`
 * (prefix `/api/admin/subscriptions`). Los `_id` llegan serializados como
 * `id` vía `serialization_alias="id"`.
 */

export type AdminPaymentStatusDto = 'pending_verification' | 'verified' | 'rejected';

export interface AdminPaymentDto {
  id: string;
  prop_id: number;
  hotel_name: string;
  owner_username: string;
  method: string;
  reference: string;
  amount: number;
  status: AdminPaymentStatusDto;
  created_at: string | null;
}

export interface AdminPaymentListDto {
  items: AdminPaymentDto[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminVerifyResponseDto {
  ok: boolean;
  payment_id: string;
  status: string;
  message: string;
}

export interface AdminRejectRequestDto {
  reason: string;
}

export interface AdminRejectResponseDto {
  ok: boolean;
  payment_id: string;
  status: string;
  message: string;
}

export interface AdminOverrideRequestDto {
  price_band?: number | null;
  price_usd?: number | null;
  notes?: string;
}

export interface AdminOverrideResponseDto {
  ok: boolean;
  id: string;
  prop_id: number;
  band: number;
  band_label: string;
  price_usd: number;
  price_band_override: boolean;
  message: string;
}

export interface AdminCancelRequestDto {
  reason?: string;
}

export interface AdminCancelResponseDto {
  ok: boolean;
  id: string;
  prop_id: number;
  status: string;
  message: string;
}

/** Referencia pública de bandas de precio (GET /api/public/pricing-plans). */
export interface PublicPricingPlanDto {
  band: number;
  label: string;
  min_rooms: number;
  max_rooms: number;
  monthly_usd: number;
  annual_monthly_usd: number;
}
