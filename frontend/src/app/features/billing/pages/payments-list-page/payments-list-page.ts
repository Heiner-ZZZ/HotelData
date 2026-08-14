import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { type PermissionCode } from '../../../../core/auth/permission.constants';
import { BillingApiService } from '../../services/billing-api.service';
import type { PaymentListItem } from '../../models/billing.model';
import { PaymentRegisterModalComponent } from '../../components/payment-register-modal/payment-register-modal';
import type { PaymentRegisterPayload } from '../../components/payment-register-modal/payment-register-modal';
import { LinkShiftModalComponent } from '../../components/link-shift-modal/link-shift-modal';

@Component({
  selector: 'app-payments-list-page',
  imports: [
    CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
    PageHeaderComponent, StatusBadgeComponent, RouterLink, FormsModule,
    PropertySelectorComponent, PaymentRegisterModalComponent, LinkShiftModalComponent,
  ],
  templateUrl: './payments-list-page.html',
  styleUrl: './payments-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaymentsListPageComponent implements OnInit {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly auth = inject(AuthService);

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));

  readonly refundingId = signal<string | null>(null);

  /** Filter: only payments without shift attribution (legacy). */
  readonly sinTurno = signal(false);

  // ── Audit filters: turno + cajero (URL-driven) ──
  readonly turnoFilter = computed(() => this.qp()?.get('turno') ?? '');
  readonly cajeroFilter = computed(() => this.qp()?.get('cajero') ?? '');

  /** Turnos del hotel para el select (degrada a vacío sin shifts.read). */
  readonly shiftOptions = signal<{ id: string; label: string }[]>([]);

  readonly activeFilterCount = computed(() => {
    let c = 0;
    if (this.turnoFilter()) c++;
    if (this.cajeroFilter()) c++;
    if (this.sinTurno()) c++;
    return c;
  });

  /** Payment being linked to a shift (opens the link modal). */
  readonly linkingPayment = signal<PaymentListItem | null>(null);

  readonly canManagePayments = computed(() => this.auth.hasPermission('payments.manage' as PermissionCode));

  // ── Register-payment modal state ──
  readonly registerOpen = signal(false);
  readonly registerSubmitting = signal(false);
  readonly registerError = signal<string | null>(null);

  openRegister(): void {
    this.registerError.set(null);
    this.registerOpen.set(true);
  }

  closeRegister(): void {
    if (this.registerSubmitting()) return;
    this.registerOpen.set(false);
  }

  registerPayment(payload: PaymentRegisterPayload): void {
    this.registerError.set(null);
    this.registerSubmitting.set(true);
    this.billingApi.createPayment({
      booking_id: payload.booking_id,
      invoice_id: payload.invoice_id || '',
      amount: payload.amount,
      method: payload.method,
      status: payload.status,
    }).subscribe({
      next: () => {
        this.toast.show('Pago registrado correctamente.', 'info', 4000);
        this.registerSubmitting.set(false);
        this.registerOpen.set(false);
        this.paymentsResource.reload();
      },
      error: (err: ApiError) => {
        this.registerSubmitting.set(false);
        this.registerError.set(err.message || 'No se pudo registrar el pago.');
      },
    });
  }

  readonly methodLabels: Record<string, { label: string; icon: string }> = {
    cash: { label: 'Efectivo', icon: 'payments' },
    card: { label: 'Tarjeta', icon: 'credit_card' },
    credit_card: { label: 'Tarjeta crédito', icon: 'credit_card' },
    bank_transfer: { label: 'Transferencia', icon: 'account_balance' },
    simulated: { label: 'Tarjeta de crédito', icon: 'credit_card' },
  };

  // ── Payments resource ──
  readonly paymentsResource = rxResource<any, any>({
    params: () => ({
      propId: this.selectedPropId() || undefined,
      page: this.currentPage(),
      sinTurno: this.sinTurno(),
      turno: this.turnoFilter() || undefined,
      cajero: this.cajeroFilter() || undefined,
    }),
    stream: ({ params }) => this.billingApi.getPayments(
      (params as any).page,
      {
        prop_id: (params as any).propId,
        sin_turno: !!(params as any).sinTurno,
        turno: (params as any).turno,
        cajero: (params as any).cajero,
      },
    ),
  });

  /** Carga las opciones de turno del hotel seleccionado para el filtro. */
  private loadShiftOptions(propId: number): void {
    if (!propId) {
      this.shiftOptions.set([]);
      return;
    }
    this.billingApi.getShiftOptions(propId).subscribe({
      next: (options) => this.shiftOptions.set(options),
      error: () => this.shiftOptions.set([]),
    });
  }

  ngOnInit(): void {
    this.loadShiftOptions(this.selectedPropId());
  }

  readonly viewState = computed<ViewState>(() => {
    const r = this.paymentsResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()?.items.length) return 'empty';
    return 'success';
  });

  readonly data = computed(() => this.paymentsResource.value());

  /** Badge del chip "Sin turno": pagos legacy del hotel pendientes de vincular. */
  readonly sinTurnoCount = computed(() => this.data()?.legacyPendingCount ?? 0);

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    this.loadShiftOptions(event.propId);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  private navigate(params: Record<string, string | null>): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: null, ...params },
      queryParamsHandling: 'merge',
    });
  }

  setTurnoFilter(id: string): void {
    const next = id === this.turnoFilter() ? '' : id;
    this.navigate({ turno: next || null });
  }

  setCajeroFilter(value: string): void {
    this.navigate({ cajero: value || null });
  }

  clearAllFilters(): void {
    this.sinTurno.set(false);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { turno: null, cajero: null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  async refund(item: PaymentListItem): Promise<void> {
    const reason = await this.confirmDialog.openPrompt({
      title: 'Reembolsar pago',
      message: '¿Reembolsar este pago? El cobro se revierte y no se puede deshacer.',
      confirmLabel: 'Reembolsar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: item.reference || item.id,
      input: {
        label: 'Motivo del reembolso (opcional)',
        placeholder: 'Ej. Cliente insatisfecho, cobro duplicado…',
        maxLength: 500,
      },
    });
    if (reason === null) return;
    this.refundingId.set(item.id);
    this.billingApi.refundPayment(item.id, this.selectedPropId(), undefined, reason)
      .subscribe({
        next: () => {
          this.toast.show('Pago reembolsado correctamente.', 'info', 4000);
          this.refundingId.set(null);
          this.paymentsResource.reload();
        },
        error: (err: ApiError) => {
          this.toast.show(err.message || 'Error al reembolsar el pago.', 'error', 5000);
          this.refundingId.set(null);
        },
      });
  }

  toggleSinTurno(): void {
    this.sinTurno.update((v) => !v);
  }

  openLinkShift(payment: PaymentListItem): void {
    this.linkingPayment.set(payment);
  }

  closeLinkShift(): void {
    this.linkingPayment.set(null);
  }

  onPaymentLinked(): void {
    this.closeLinkShift();
    this.toast.show('Pago vinculado al turno correctamente.', 'info', 4000);
    this.paymentsResource.reload();
  }

  /** A payment is linkable when it has no shift attribution at all. */
  canLink(item: PaymentListItem): boolean {
    return this.canManagePayments() && !this.shiftLabel(item);
  }

  getMethodInfo(method: string) {
    return this.methodLabels[method] ?? { label: method, icon: 'receipt' };
  }

  readonly statusLabels: Record<string, { label: string; tone: 'success' | 'warning' | 'danger' | 'neutral' }> = {
    confirmed: { label: 'Confirmado', tone: 'success' },
    refunded: { label: 'Reembolsado', tone: 'warning' },
    failed: { label: 'Fallido', tone: 'danger' },
    rejected: { label: 'Rechazado', tone: 'danger' },
    declined: { label: 'Declinado', tone: 'danger' },
    error: { label: 'Error', tone: 'danger' },
  };

  getStatusInfo(status: string) {
    return this.statusLabels[status] ?? { label: status, tone: 'neutral' as const };
  }

  /** Responsible cashier label: refund shift wins when the payment was refunded. */
  shiftLabel(item: PaymentListItem): string | null {
    if (item.status === 'refunded' && item.refundShiftEmployee) return item.refundShiftEmployee;
    return item.shiftEmployee || item.shiftOpenedBy || null;
  }

  /** Tooltip with the shift FK + type for full attribution. */
  shiftTitle(item: PaymentListItem): string {
    const id = item.status === 'refunded' && item.refundShiftId ? item.refundShiftId : item.shiftId;
    const type = item.shiftType ? ` · ${item.shiftType}` : '';
    return id ? `Turno ${id}${type}` : 'Sin turno asociado';
  }

  printPage() {
    window.print();
  }
}
