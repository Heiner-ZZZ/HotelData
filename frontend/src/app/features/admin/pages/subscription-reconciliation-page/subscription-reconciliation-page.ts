import { CurrencyPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { API_CONFIG } from '../../../../core/api/api.config';
import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { getErrorMessage } from '../../../../shared/utils/http-error.util';
import type {
  AdminPaymentListDto,
  PublicPricingPlanDto,
} from '../../models/reconciliation.dto';
import {
  mapAdminPaymentQueue,
  mapPricingBand,
  type AdminPayment,
  type AdminPaymentQueue,
  type AdminPaymentStatus,
  type PricingBandOption,
} from '../../models/reconciliation.model';
import { ReconciliationApiService } from '../../services/reconciliation-api.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';

type QueueFilter = 'pending_verification' | 'verified' | 'rejected' | 'all';
type Tone = 'neutral' | 'success' | 'warning' | 'danger';

const PAYMENT_STATUS_META: Record<AdminPaymentStatus, { label: string; tone: Tone }> = {
  pending_verification: { label: 'Pendiente', tone: 'warning' },
  verified: { label: 'Verificado', tone: 'success' },
  rejected: { label: 'Rechazado', tone: 'danger' },
};

const METHOD_LABELS: Record<string, string> = {
  bank_transfer: 'Transferencia',
  cash_deposit: 'Depósito',
  manual_online: 'Pago en línea',
};

@Component({
  selector: 'app-subscription-reconciliation-page',
  imports: [
    CurrencyPipe,
    PageHeaderComponent,
    StatusBadgeComponent,
    LoadingStateComponent,
    ErrorStateComponent,
    EmptyStateComponent,
    PropertySelectorComponent,
  ],
  templateUrl: './subscription-reconciliation-page.html',
  styleUrl: './subscription-reconciliation-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SubscriptionReconciliationPageComponent {
  private readonly api = inject(ReconciliationApiService);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);
  readonly propCtx = inject(PropertyContextService);

  // ── Cola de comprobantes (GET por httpResource) ─────────────────────
  readonly filterTabs: { key: QueueFilter; label: string }[] = [
    { key: 'pending_verification', label: 'Pendientes' },
    { key: 'verified', label: 'Verificados' },
    { key: 'rejected', label: 'Rechazados' },
    { key: 'all', label: 'Todos' },
  ];

  readonly statusFilter = signal<QueueFilter>('pending_verification');
  readonly currentPage = signal(1);

  readonly paymentsResource = httpResource<AdminPaymentQueue>(
    () => {
      const status = this.statusFilter();
      const statusParam = status === 'all' ? '' : `&status=${status}`;
      return `${this.apiConfig.baseUrl}/admin/subscriptions/payments?page=${this.currentPage()}${statusParam}`;
    },
    { parse: (dto) => mapAdminPaymentQueue(dto as AdminPaymentListDto) },
  );

  readonly bandsResource = httpResource<PricingBandOption[]>(
    () => `${this.apiConfig.baseUrl}/public/pricing-plans`,
    {
      parse: (dto) =>
        ((dto as { plans: PublicPricingPlanDto[] }).plans ?? []).map(mapPricingBand),
    },
  );

  readonly payments = computed<AdminPayment[]>(() => {
    if (this.paymentsResource.error()) return [];
    return this.paymentsResource.value()?.items ?? [];
  });

  readonly queue = computed<AdminPaymentQueue | null>(() => {
    if (this.paymentsResource.error()) return null;
    return this.paymentsResource.value() ?? null;
  });

  readonly bands = computed<PricingBandOption[]>(() => {
    if (this.bandsResource.error()) return [];
    return this.bandsResource.value() ?? [];
  });

  readonly viewState = computed<'loading' | 'error' | 'empty' | 'success'>(() => {
    if (this.paymentsResource.error()) return 'error';
    if (this.paymentsResource.isLoading()) return 'loading';
    return this.payments().length ? 'success' : 'empty';
  });

  readonly totalPages = computed<number>(() => {
    const q = this.queue();
    if (!q || q.pageSize <= 0) return 1;
    return Math.max(1, Math.ceil(q.total / q.pageSize));
  });

  /** id del comprobante en vuelo (verify/reject) — desactiva acciones. */
  readonly busyPaymentId = signal<string | null>(null);

  // ── Gestionar suscripción (override / cancel) ───────────────────────
  /** Selección explícita del selector global (modo all/multi). */
  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  /**
   * Hotel objetivo compartido por override y cancel. En single-hotel se
   * deriva del contexto (el selector global no emite `propIdChange` ahí);
   * en all/multi usa la selección explícita del usuario.
   */
  readonly targetPropId = computed(() =>
    this.propCtx.singleHotelMode() ? this.propCtx.defaultPropId() : this.selectedPropId(),
  );

  readonly targetLabel = computed(() => {
    if (this.propCtx.singleHotelMode()) {
      return this.propCtx.currentPropLabel() || `Propiedad #${this.propCtx.defaultPropId()}`;
    }
    return this.selectedLabel();
  });

  readonly overrideBand = signal<number | null>(null);
  readonly overridePrice = signal<number | null>(null);
  readonly overrideNotes = signal('');
  readonly overrideSaving = signal(false);
  readonly overrideError = signal('');

  readonly cancelReason = signal('');
  readonly cancelSaving = signal(false);
  readonly cancelError = signal('');

  // ── Helpers de presentación ─────────────────────────────────────────
  parseNumber(raw: unknown): number | null {
    const value = typeof raw === 'string' ? raw.trim() : raw;
    if (value === '' || value === null || value === undefined) return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  setFilter(status: QueueFilter): void {
    this.statusFilter.set(status);
    this.currentPage.set(1);
  }

  goToPage(page: number): void {
    this.currentPage.set(page);
  }

  pagesArray(): number[] {
    return Array.from({ length: this.totalPages() }, (_, i) => i + 1);
  }

  paymentStatusLabel(status: AdminPaymentStatus): string {
    return PAYMENT_STATUS_META[status]?.label ?? status;
  }

  paymentStatusTone(status: AdminPaymentStatus): Tone {
    return PAYMENT_STATUS_META[status]?.tone ?? 'neutral';
  }

  methodLabel(method: string): string {
    return METHOD_LABELS[method] ?? method;
  }

  formatDate(iso: string | null): string {
    if (!iso) return '—';
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('es', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }

  // ── verify / reject ─────────────────────────────────────────────────
  async verify(payment: AdminPayment): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Verificar pago',
      message: `Confirmar el comprobante de ${payment.hotelName}. La factura quedará pagada y la suscripción activa.`,
      confirmLabel: 'Verificar pago',
      cancelLabel: 'Cancelar',
      variant: 'default',
      details: [
        `Hotel: ${payment.hotelName}`,
        `Dueño: ${payment.ownerUsername || '—'}`,
        `Referencia: ${payment.reference || '—'}`,
        `Monto: ${payment.amount} USD`,
      ],
    });
    if (!ok) return;

    this.busyPaymentId.set(payment.id);
    this.api
      .verify(payment.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.busyPaymentId.set(null);
          this.toast.show(res.message || 'Pago verificado.', 'success', 5000);
          this.paymentsResource.reload();
        },
        error: (err: unknown) => {
          this.busyPaymentId.set(null);
          this.toast.show(getErrorMessage(err) || 'No se pudo verificar el pago.', 'error', 6000);
        },
      });
  }

  async reject(payment: AdminPayment): Promise<void> {
    const reason = await this.confirmDialog.openPrompt({
      title: 'Rechazar comprobante',
      message: `Rechazar el comprobante de ${payment.hotelName}. La suscripción volverá a pago pendiente.`,
      confirmLabel: 'Rechazar',
      cancelLabel: 'Cancelar',
      variant: 'danger',
      input: {
        label: 'Motivo del rechazo',
        placeholder: 'Ej. Comprobante ilegible, monto no coincide…',
        required: true,
        maxLength: 500,
      },
    });
    if (reason === null || !reason.trim()) return;

    this.busyPaymentId.set(payment.id);
    this.api
      .reject(payment.id, reason.trim())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.busyPaymentId.set(null);
          this.toast.show(res.message || 'Comprobante rechazado.', 'warning', 5000);
          this.paymentsResource.reload();
        },
        error: (err: unknown) => {
          this.busyPaymentId.set(null);
          this.toast.show(getErrorMessage(err) || 'No se pudo rechazar el comprobante.', 'error', 6000);
        },
      });
  }

  // ── override / cancel ───────────────────────────────────────────────
  onTargetPropSelected(event: { propId: number; label: string }): void {
    this.selectedPropId.set(event.propId);
    this.selectedLabel.set(event.label || `Propiedad #${event.propId}`);
  }

  async submitOverride(): Promise<void> {
    const propId = this.targetPropId();
    const label = this.targetLabel() || `Propiedad #${propId}`;
    const band = this.overrideBand();
    const price = this.overridePrice();
    if (propId <= 0) {
      this.overrideError.set('Selecciona un hotel.');
      return;
    }
    if (band === null && price === null) {
      this.overrideError.set('Indica una banda o un precio para el override.');
      return;
    }

    const ok = await this.confirmDialog.open({
      title: 'Aplicar precio negociado',
      message: `Se aplicará un override de precio a la suscripción de ${label}. Quedará marcada como precio negociado.`,
      confirmLabel: 'Aplicar override',
      cancelLabel: 'Cancelar',
      variant: 'warning',
      details: [
        `Hotel: ${label}`,
        band !== null ? `Banda: ${band}` : 'Banda: sin cambio',
        price !== null ? `Precio: ${price} USD/mes` : 'Precio: sin cambio',
      ],
    });
    if (!ok) return;

    this.overrideSaving.set(true);
    this.overrideError.set('');
    this.api
      .override(propId, {
        price_band: band,
        price_usd: price,
        notes: this.overrideNotes().trim(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.overrideSaving.set(false);
          this.toast.show(res.message || 'Override de precio aplicado.', 'success', 5000);
          this.overrideBand.set(null);
          this.overridePrice.set(null);
          this.overrideNotes.set('');
        },
        error: (err: unknown) => {
          this.overrideSaving.set(false);
          this.overrideError.set(getErrorMessage(err) || 'No se pudo aplicar el override.');
        },
      });
  }

  async submitCancel(): Promise<void> {
    const propId = this.targetPropId();
    const label = this.targetLabel() || `Propiedad #${propId}`;
    if (propId <= 0) {
      this.cancelError.set('Selecciona un hotel.');
      return;
    }

    const ok = await this.confirmDialog.open({
      title: 'Cancelar suscripción',
      message: `Cancelar la suscripción de ${label}. Es irreversible: el hotel quedará fuera de operaciones y sin publicar.`,
      confirmLabel: 'Cancelar suscripción',
      cancelLabel: 'Volver',
      variant: 'danger',
      mode: 'delete',
      modeDetail: `Suscripción de ${label}`,
    });
    if (!ok) return;

    this.cancelSaving.set(true);
    this.cancelError.set('');
    this.api
      .cancel(propId, this.cancelReason().trim())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.cancelSaving.set(false);
          this.toast.show(res.message || 'Suscripción cancelada.', 'success', 5000);
          this.cancelReason.set('');
        },
        error: (err: unknown) => {
          this.cancelSaving.set(false);
          this.cancelError.set(getErrorMessage(err) || 'No se pudo cancelar la suscripción.');
        },
      });
  }
}
