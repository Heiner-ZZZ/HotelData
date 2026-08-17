import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { API_CONFIG } from '../../../../core/api/api.config';
import { toast } from '../../../../core/toast/toast.service';
import { getErrorMessage } from '../../../../shared/utils/http-error.util';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type {
  SubscriptionInvoicesDto,
  SubscriptionMeDto,
} from '../../models/subscription.dto';
import {
  mapSubscriptionInvoices,
  mapSubscriptionMe,
  type SubscriptionInvoice,
  type SubscriptionMe,
  type SubscriptionStatus,
} from '../../models/subscription.model';
import { SubscriptionApiService } from '../../services/subscription-api.service';

type Tone = 'neutral' | 'success' | 'warning' | 'danger';

const STATUS_META: Record<SubscriptionStatus, { label: string; icon: string; tone: Tone }> = {
  pending_payment: { label: 'Pago pendiente', icon: 'hourglass_top', tone: 'warning' },
  payment_submitted: { label: 'Comprobante en verificación', icon: 'fact_check', tone: 'neutral' },
  active: { label: 'Activa', icon: 'check_circle', tone: 'success' },
  overdue: { label: 'Vencida', icon: 'warning', tone: 'danger' },
  suspended: { label: 'Suspendida', icon: 'pause_circle', tone: 'danger' },
  cancelled: { label: 'Cancelada', icon: 'cancel', tone: 'neutral' },
};

const INVOICE_STATUS_META: Record<string, { label: string; tone: Tone }> = {
  unpaid: { label: 'Pendiente', tone: 'warning' },
  paid: { label: 'Pagada', tone: 'success' },
  overdue: { label: 'Vencida', tone: 'danger' },
  void: { label: 'Anulada', tone: 'neutral' },
};

@Component({
  selector: 'app-my-subscription-page',
  imports: [
    DecimalPipe,
    ReactiveFormsModule,
    PageHeaderComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    ErrorStateComponent,
    EmptyStateComponent,
  ],
  templateUrl: './my-subscription-page.html',
  styleUrl: './my-subscription-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MySubscriptionPageComponent {
  private readonly api = inject(SubscriptionApiService);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  // ── Recursos GET (httpResource por convención) ──────────────────────
  readonly subscriptionResource = httpResource<SubscriptionMe>(
    () => `${this.apiConfig.baseUrl}/billing/subscriptions/me`,
    { parse: (dto) => mapSubscriptionMe(dto as SubscriptionMeDto) },
  );

  readonly invoicesResource = httpResource<SubscriptionInvoice[]>(
    () => `${this.apiConfig.baseUrl}/billing/subscriptions/me/invoices`,
    { parse: (dto) => mapSubscriptionInvoices(dto as SubscriptionInvoicesDto) },
  );

  /** Valor seguro: no re-lanza el error del recurso en el template. */
  readonly subscription = computed<SubscriptionMe | null>(() => {
    if (this.subscriptionResource.error()) return null;
    return this.subscriptionResource.value() ?? null;
  });

  readonly invoices = computed<SubscriptionInvoice[]>(
    () => this.invoicesResource.value() ?? [],
  );

  readonly viewState = computed<ViewState>(() => {
    if (this.subscriptionResource.isLoading()) return 'loading';
    if (this.subscriptionResource.error()) return 'error';
    return this.subscriptionResource.value() ? 'success' : 'loading';
  });

  // ── Factura pendiente ───────────────────────────────────────────────
  readonly unpaidInvoice = computed<SubscriptionInvoice | null>(() => {
    const next = this.subscription()?.nextInvoice;
    if (next && (next.status === 'unpaid' || next.status === 'overdue')) return next;
    const list = this.invoices();
    return list.find((i) => i.status === 'unpaid' || i.status === 'overdue') ?? null;
  });

  /** Solo se puede registrar comprobante si hay factura y el estado lo permite. */
  readonly canPay = computed<boolean>(() => {
    const s = this.subscription()?.status;
    return !!this.unpaidInvoice() && (s === 'pending_payment' || s === 'overdue' || s === 'suspended');
  });

  readonly isOverdueOrSuspended = computed<boolean>(() => {
    const s = this.subscription()?.status;
    return s === 'overdue' || s === 'suspended';
  });

  // ── Formulario de comprobante ───────────────────────────────────────
  readonly paySaving = signal(false);
  readonly payError = signal('');

  readonly payForm = this.formBuilder.nonNullable.group({
    method: ['', [Validators.required]],
    reference: ['', [Validators.required, Validators.minLength(3)]],
    amount: [0, [Validators.required, Validators.min(0.01)]],
  });

  readonly selectedMethodCode = toSignal(this.payForm.controls.method.valueChanges, {
    initialValue: this.payForm.controls.method.value,
  });

  /** Datos de la cuenta destino del método seleccionado (catálogo). */
  readonly selectedMethodDetails = computed<{ label: string; value: string }[]>(() => {
    const code = this.selectedMethodCode();
    const sub = this.subscription();
    if (!code || !sub) return [];
    const method = sub.paymentMethods.find((m) => m.code === code);
    if (!method) return [];
    const details = method.details ?? {};
    const keys: [string, string][] = [
      ['bank_name', 'Banco'],
      ['account_holder', 'Titular'],
      ['account_number', 'Número de cuenta'],
      ['instructions', 'Instrucciones'],
    ];
    return keys
      .filter(([key]) => (details[key] ?? '').trim() !== '')
      .map(([key, label]) => ({ label, value: details[key] }));
  });

  /** Pre-rellena método + monto con la factura pendiente al cargar. */
  private readonly prefillPayForm = effect(() => {
    const inv = this.unpaidInvoice();
    const sub = this.subscription();
    if (!inv || !sub) return;
    const method =
      sub.paymentMethod ??
      (sub.paymentMethods.length ? sub.paymentMethods[0].code : '');
    // emitEvent:true para que `selectedMethodCode` (toSignal del valueChanges)
    // refresque los datos de cuenta del método pre-seleccionado.
    this.payForm.patchValue({ method, amount: inv.amountUsd });
  });

  submitPayment(): void {
    if (this.payForm.invalid || this.paySaving()) {
      this.payForm.markAllAsTouched();
      return;
    }
    const inv = this.unpaidInvoice();
    if (!inv) {
      this.payError.set('No hay una factura pendiente de pago.');
      return;
    }
    const raw = this.payForm.getRawValue();
    this.paySaving.set(true);
    this.payError.set('');
    this.api
      .pay({
        invoice_id: inv.id,
        method: raw.method,
        reference: raw.reference,
        amount: raw.amount,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.paySaving.set(false);
          toast(res.message || 'Comprobante registrado. Está pendiente de verificación.', 'success');
          this.subscriptionResource.reload();
          this.invoicesResource.reload();
        },
        error: (err: unknown) => {
          this.paySaving.set(false);
          this.payError.set(getErrorMessage(err) || 'No se pudo registrar el comprobante.');
        },
      });
  }

  // ── Helpers de presentación ─────────────────────────────────────────
  statusLabel(s: SubscriptionStatus): string {
    return STATUS_META[s]?.label ?? s;
  }

  statusIcon(s: SubscriptionStatus): string {
    return STATUS_META[s]?.icon ?? 'info';
  }

  statusTone(s: SubscriptionStatus): Tone {
    return STATUS_META[s]?.tone ?? 'neutral';
  }

  invoiceStatusLabel(s: string): string {
    return INVOICE_STATUS_META[s]?.label ?? s;
  }

  invoiceStatusTone(s: string): Tone {
    return INVOICE_STATUS_META[s]?.tone ?? 'neutral';
  }

  cycleLabel(cycle: string): string {
    return cycle === 'annual' ? 'Anual' : 'Mensual';
  }

  /** Fecha ISO → local (es). */
  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '—';
    return new Intl.DateTimeFormat('es', {
      dateStyle: 'medium',
    }).format(date);
  }

  /** Nombre del método de pago por código (catálogo de la suscripción). */
  methodLabel(code: string): string {
    const sub = this.subscription();
    if (!sub) return code;
    return sub.paymentMethods.find((m) => m.code === code)?.label ?? code;
  }
}
