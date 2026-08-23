/**
 * Wire shape de la pantalla del dueño pendiente (UX-3).
 *
 * KEEP IN SYNC con `server/src/app/modules/auth/routes/registration_status.py`
 * (`GET /api/auth/registration-status` y `PATCH /api/auth/register-property/me`).
 */

export type ApprovalStatusDto =
  | 'pending_approval'
  | 'changes_requested'
  | 'rejected'
  | 'approved';

export interface RegistrationStatusDto {
  approval_status: ApprovalStatusDto;
  rejected_reason: string | null;
  feedback: string | null;
  submitted_at: string | null;
  status_changed_at: string | null;
  property: RegistrationPropertyDto;
  suggested_band: SuggestedBandDto | null;
  /** Gracia inicial de la primera factura (días tras la aprobación). */
  initial_grace_days: number;
  /** Métodos de pago manuales del catálogo (sin pasarela bancaria). */
  payment_methods: PaymentMethodDto[];
  timeline: TimelineEventDto[];
}

export interface PaymentMethodDto {
  code: string;
  label: string;
  sort_order: number;
  details: Record<string, string>;
}

export interface RegistrationPropertyDto {
  name: string;
  type: string;
  city: string;
  country: string;
  total_rooms: number;
  currency: string;
  contact_phone: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
}

export interface SuggestedBandDto {
  band: number;
  label: string;
  monthly_usd: number;
  /** Cuota mensual equivalente pagando el año por adelantado (~22–27% off). */
  annual_monthly_usd: number;
  min_rooms: number;
  max_rooms: number;
}

export interface TimelineEventDto {
  event: string;
  at: string | null;
  detail: string;
}

export interface EditPropertyPayloadDto {
  property_name: string;
  property_type: string;
  contact_phone: string;
  city: string;
  total_rooms: number;
  description: string;
  address?: string;
  latitude?: number | null;
  longitude?: number | null;
}

export interface PatchPropertyResponseDto {
  ok: boolean;
  approval_status: string;
  suggested_band: SuggestedBandDto | null;
  message: string;
}
