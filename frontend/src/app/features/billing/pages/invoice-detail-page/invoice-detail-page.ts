import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceDetailViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-invoice-detail-page',
  imports: [ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent],
  templateUrl: './invoice-detail-page.html',
  styleUrl: './invoice-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoiceDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly invoice = signal<InvoiceDetailViewModel | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);

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

  cancelInvoice() {
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.cancelInvoice(this.invoice()!.id).subscribe({
      next: () => {
        this.actionMessage.set('Factura anulada correctamente.');
        this.invoice.update(i => i ? { ...i, status: 'cancelled' } : i);
      },
      error: () => this.actionError.set('No se pudo anular la factura. Intenta nuevamente.'),
    });
  }

  goBack() {
    void this.router.navigate(['/management/billing/invoices']);
  }
}
