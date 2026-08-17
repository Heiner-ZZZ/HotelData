/**
 * Wire shapes de la suscripción del dueño (PLAN_SUSCRIPCION_Y_PAGOS.md §6.1).
 *
 * KEEP IN SYNC con `server/src/app/modules/subscriptions/routes.py`
 * (prefix `/api/billing/subscriptions`). Los `id` llegan serializados desde
 * `_id` vía `serialization_alias="id"`.
 */

export type SubscriptionStatusDto =
  | 'pending_payment'
  | 'payment_submitted'
  | 'active'
  | 'overdue'
  | 'suspended'
  | 'cancelled';

export type SubscriptionInvoiceStatusDto = 'unpaid' | 'paid' | 'overdue' | 'void';

export interface SubscriptionInvoiceDto {
  id: string;
  prop_id: number;
  invoice_number: string;
  period_start: string | null;
  period_end: string | null;
  amount_usd: number;
  currency: string;
  status: SubscriptionInvoiceStatusDto;
  due_date: string | null;
  paid_at: string | null;
}

export interface SubscriptionPaymentMethodDto {
  code: string;
  label: string;
  sort_order: number;
  details: Record<string, string>;
  is_active?: boolean;
}

export interface SubscriptionMeDto {
  id: string;
  prop_id: number;
  band: number;
  band_label: string;
  billing_cycle: 'monthly' | 'annual';
  price_usd: number;
  currency: string;
  payment_method: string | null;
  status: SubscriptionStatusDto;
  renews_at: string | null;
  current_period_end: string | null;
  next_invoice: SubscriptionInvoiceDto | null;
  payment_methods: SubscriptionPaymentMethodDto[];
}

export interface SubscriptionInvoicesDto {
  items: SubscriptionInvoiceDto[];
}

export interface PaySubscriptionRequestDto {
  invoice_id: string;
  method: string;
  reference: string;
  amount: number;
}

export interface PaySubscriptionResponseDto {
  ok: boolean;
  id: string;
  status: string;
  message: string;
}

export interface ChooseSubscriptionRequestDto {
  band: number;
  billing_cycle: 'monthly' | 'annual';
  payment_method: string;
}

export interface ChooseSubscriptionResponseDto {
  ok: boolean;
  band: number;
  billing_cycle: string;
  payment_method: string;
  price_usd: number;
  message: string;
}
