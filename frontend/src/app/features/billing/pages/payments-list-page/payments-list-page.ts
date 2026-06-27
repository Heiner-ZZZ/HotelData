import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { CurrencyPipe } from '@angular/common';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { toast } from '../../../../core/toast/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { PaymentsListViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-payments-list-page',
  imports: [CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, RouterLink],
  templateUrl: './payments-list-page.html',
  styleUrl: './payments-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PaymentsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaymentsListViewModel | null>(null);
  readonly refundingId = signal<string | null>(null);

  readonly methodLabels: Record<string, { label: string; icon: string }> = {
    cash: { label: 'Efectivo', icon: 'payments' },
    credit_card: { label: 'Tarjeta crédito', icon: 'credit_card' },
    bank_transfer: { label: 'Transferencia', icon: 'account_balance' },
    simulated: { label: 'Tarjeta de crédito', icon: 'credit_card' },
  };

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map(params => Number(params.get('page') ?? '1')),
        distinctUntilChanged(),
        switchMap(page => {
          this.viewState.set('loading');
          return this.billingApi.getPayments(page);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: data => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
    });
  }

  refund(paymentId: string) {
    this.refundingId.set(paymentId);
    this.billingApi.refundPayment(paymentId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          toast('Pago reembolsado correctamente.', 'dark', 4000);
          this.refundingId.set(null);
          this.goToPage(this.data()?.page ?? 1);
        },
        error: (err: ApiError) => {
          toast(err.message || 'Error al reembolsar el pago.', 'error', 5000);
          this.refundingId.set(null);
        },
      });
  }

  getMethodInfo(method: string) {
    return this.methodLabels[method] ?? { label: method, icon: 'receipt' };
  }

  printPage() {
    window.print();
  }
}
