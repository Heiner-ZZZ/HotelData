import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { switchMap } from 'rxjs';

import { CurrencyPipe, DatePipe } from '@angular/common';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceDetailViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-client-invoice-detail-page',
  imports: [CurrencyPipe, DatePipe, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent],
  templateUrl: './client-invoice-detail-page.html',
  styleUrl: './client-invoice-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientInvoiceDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly invoice = signal<InvoiceDetailViewModel | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly paying = signal(false);
  readonly paymentStep = signal<'idle' | 'processing' | 'confirm' | 'done'>('idle');
  readonly paymentReference = signal('');
  readonly today = signal(new Date().toLocaleDateString('es-MX', {
    year: 'numeric', month: 'long', day: 'numeric',
  }));

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        switchMap(params => {
          this.viewState.set('loading');
          return this.billingApi.getInvoiceDetail(params.get('invoiceId')!);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: data => {
          this.invoice.set(data);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
      });
  }

  startPayment() {
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.paymentStep.set('processing');
    this.paying.set(true);

    // Simulated processing delay like a real banking system
    setTimeout(() => {
      this.paymentStep.set('confirm');
      this.paying.set(false);
    }, 2000);
  }

  confirmPayment() {
    const inv = this.invoice();
    if (!inv) return;

    this.paying.set(true);
    this.actionError.set(null);

    this.billingApi.payMyInvoice(inv.id).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        this.paymentReference.set(result.payment?.['reference'] as string || '');
        this.paymentStep.set('done');
        this.paying.set(false);
        this.invoice.update(i => i ? { ...i, status: 'paid', paidAt: new Date().toISOString() } : i);
      },
      error: (err) => {
        this.actionError.set(err.message || 'Error al procesar el pago. Intenta nuevamente.');
        this.paymentStep.set('idle');
        this.paying.set(false);
      },
    });
  }

  cancelPayment() {
    this.paymentStep.set('idle');
    this.paying.set(false);
  }

  goBack() {
    void this.router.navigate(['/account/billing']);
  }
}
