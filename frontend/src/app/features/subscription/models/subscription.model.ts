/** View models tipados de la suscripción del dueño + mappers wire → model. */
import type {
  SubscriptionInvoiceDto,
  SubscriptionInvoicesDto,
  SubscriptionMeDto,
  SubscriptionPaymentMethodDto,
} from './subscription.dto';

export type SubscriptionStatus =
  | 'pending_payment'
  | 'payment_submitted'
  | 'active'
  | 'overdue'
  | 'suspended'
  | 'cancelled';

export type SubscriptionInvoiceStatus = 'unpaid' | 'paid' | 'overdue' | 'void';

export interface SubscriptionInvoice {
  id: string;
  propId: number;
  invoiceNumber: string;
  periodStart: string | null;
  periodEnd: string | null;
  amountUsd: number;
  currency: string;
  status: SubscriptionInvoiceStatus;
  dueDate: string | null;
  paidAt: string | null;
}

export interface SubscriptionPaymentMethod {
  code: string;
  label: string;
  sortOrder: number;
  details: Record<string, string>;
}

export interface SubscriptionMe {
  id: string;
  propId: number;
  band: number;
  bandLabel: string;
  billingCycle: 'monthly' | 'annual';
  priceUsd: number;
  currency: string;
  paymentMethod: string | null;
  status: SubscriptionStatus;
  renewsAt: string | null;
  currentPeriodEnd: string | null;
  nextInvoice: SubscriptionInvoice | null;
  paymentMethods: SubscriptionPaymentMethod[];
}

export function mapSubscriptionInvoice(dto: SubscriptionInvoiceDto): SubscriptionInvoice {
  return {
    id: dto.id,
    propId: dto.prop_id,
    invoiceNumber: dto.invoice_number,
    periodStart: dto.period_start ?? null,
    periodEnd: dto.period_end ?? null,
    amountUsd: dto.amount_usd,
    currency: dto.currency,
    status: dto.status,
    dueDate: dto.due_date ?? null,
    paidAt: dto.paid_at ?? null,
  };
}

export function mapPaymentMethod(dto: SubscriptionPaymentMethodDto): SubscriptionPaymentMethod {
  return {
    code: dto.code,
    label: dto.label,
    sortOrder: dto.sort_order,
    details: dto.details ?? {},
  };
}

export function mapSubscriptionMe(dto: SubscriptionMeDto): SubscriptionMe {
  return {
    id: dto.id,
    propId: dto.prop_id,
    band: dto.band,
    bandLabel: dto.band_label,
    billingCycle: dto.billing_cycle,
    priceUsd: dto.price_usd,
    currency: dto.currency,
    paymentMethod: dto.payment_method ?? null,
    status: dto.status,
    renewsAt: dto.renews_at ?? null,
    currentPeriodEnd: dto.current_period_end ?? null,
    nextInvoice: dto.next_invoice ? mapSubscriptionInvoice(dto.next_invoice) : null,
    paymentMethods: (dto.payment_methods ?? []).map(mapPaymentMethod),
  };
}

export function mapSubscriptionInvoices(dto: SubscriptionInvoicesDto): SubscriptionInvoice[] {
  return (dto.items ?? []).map(mapSubscriptionInvoice);
}
