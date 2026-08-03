import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
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
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { type PermissionCode } from '../../../../core/auth/permission.constants';
import { BillingApiService } from '../../services/billing-api.service';
import { PaymentRegisterModalComponent } from '../../components/payment-register-modal/payment-register-modal';
import type { PaymentRegisterPayload } from '../../components/payment-register-modal/payment-register-modal';

@Component({
  selector: 'app-payments-list-page',
  imports: [
    CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
    PageHeaderComponent, StatusBadgeComponent, RouterLink, FormsModule,
    PropertySelectorComponent, PaymentRegisterModalComponent,
  ],
  templateUrl: './payments-list-page.html',
  styleUrl: './payments-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaymentsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
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
    }),
    stream: ({ params }) => this.billingApi.getPayments(
      (params as any).page,
      { prop_id: (params as any).propId },
    ),
  });

  readonly viewState = computed<ViewState>(() => {
    const r = this.paymentsResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()?.items.length) return 'empty';
    return 'success';
  });

  readonly data = computed(() => this.paymentsResource.value());

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
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

  refund(paymentId: string) {
    this.refundingId.set(paymentId);
    this.billingApi.refundPayment(paymentId)
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

  printPage() {
    window.print();
  }
}
