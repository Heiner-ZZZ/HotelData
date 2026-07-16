import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { map } from 'rxjs';

import { CurrencyPipe, DatePipe } from '@angular/common';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceDetailViewModel } from '../../models/billing.model';
import { mapInvoiceDetail } from '../../mappers/billing.mapper';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-client-invoice-detail-page',
  imports: [CurrencyPipe, DatePipe, ErrorStateComponent, LoadingStateComponent, StatusBadgeComponent],
  templateUrl: './client-invoice-detail-page.html',
  styleUrl: './client-invoice-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ClientInvoiceDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  private readonly invoiceId = toSignal(
    this.activatedRoute.paramMap.pipe(map(params => params.get('invoiceId') ?? '')),
    { initialValue: '' }
  );

  readonly invoiceResource = httpResource<InvoiceDetailViewModel>(() => {
    const id = this.invoiceId();
    return id ? `/api/billing/invoices/${id}` : undefined;
  }, {
    parse: (res) => mapInvoiceDetail(res as import('../../models/billing.dto').InvoiceDetailDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.invoiceResource.isLoading()) return 'loading';
    if (this.invoiceResource.error()) return 'error';
    return this.invoiceResource.value() ? 'success' : 'loading';
  });

  readonly invoice = computed(() => this.invoiceResource.value() ?? null);
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly paying = signal(false);
  readonly paymentStep = signal<'idle' | 'processing' | 'confirm' | 'done'>('idle');
  readonly paymentReference = signal('');
  readonly today = signal(new Date().toLocaleDateString('es-MX', {
    year: 'numeric', month: 'long', day: 'numeric',
  }));

  constructor() {}

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

    this.billingApi.payMyInvoice(inv.id).subscribe({
      next: (result) => {
        this.paymentReference.set(result.payment?.['reference'] as string || '');
        this.paymentStep.set('done');
        this.paying.set(false);
        this.invoiceResource.reload();
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
