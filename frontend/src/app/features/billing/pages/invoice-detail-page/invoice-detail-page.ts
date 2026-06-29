import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceDetailViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-invoice-detail-page',
  imports: [CurrencyPipe, DatePipe, RouterLink, ErrorStateComponent, LoadingStateComponent, EmptyStateComponent],
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

  readonly isPaid = computed(() => this.invoice()?.status === 'paid');
  readonly isCancelled = computed(() => this.invoice()?.status === 'cancelled');
  readonly isIssued = computed(() => this.invoice()?.status === 'issued');

  readonly subtotal = computed(() => this.invoice()?.subtotal ?? 0);
  readonly taxes = computed(() => this.invoice()?.taxes ?? 0);
  readonly total = computed(() => this.invoice()?.total ?? 0);
  readonly extrasTotal = computed(() => this.invoice()?.extrasTotal ?? 0);
  readonly roomSubtotal = computed(() => this.invoice()?.roomSubtotal ?? 0);
  readonly lineItems = computed(() => this.invoice()?.lineItems ?? []);
  readonly payments = computed(() => this.invoice()?.payments ?? []);

  readonly discount = computed(() => {
    const s = this.subtotal();
    const r = this.roomSubtotal();
    const e = this.extrasTotal();
    const expected = r + e;
    return expected > 0 ? Math.round((expected - s) * 100) / 100 : 0;
  });

  readonly totalLiteral = computed(() => {
    const t = this.total();
    if (t === 0) return 'Cero pesos 00/100 M.N.';
    const intPart = Math.floor(t);
    const decPart = Math.round((t - intPart) * 100);
    return `${_numToWords(intPart)} pesos ${String(decPart).padStart(2, '0')}/100 M.N.`;
  });

  readonly statusLabel = computed(() => {
    const s = this.invoice()?.status;
    if (s === 'paid') return 'Pagada';
    if (s === 'cancelled') return 'Anulada';
    if (s === 'refunded') return 'Reembolsada';
    return 'Emitida';
  });

  readonly statusTone = computed(() => {
    const s = this.invoice()?.status;
    if (s === 'paid') return 'success';
    if (s === 'cancelled' || s === 'refunded') return 'danger';
    return 'warning';
  });

  readonly taxRate = computed(() => {
    const s = this.subtotal();
    const t = this.taxes();
    return s > 0 ? (t / s) * 100 : 0;
  });

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        switchMap((params) => {
          this.viewState.set('loading');
          return this.billingApi.getInvoiceDetail(params.get('invoiceId')!);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.invoice.set(data);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
      });
  }

  payInvoice(): void {
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.payInvoice(this.invoice()!.id).subscribe({
      next: () => {
        this.actionMessage.set('Pago procesado exitosamente.');
        this.invoice.update((i) => (i ? { ...i, status: 'paid' } : i));
      },
      error: () => this.actionError.set('No se pudo procesar el pago.'),
    });
  }

  cancelInvoice(): void {
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.cancelInvoice(this.invoice()!.id).subscribe({
      next: () => {
        this.actionMessage.set('Factura anulada correctamente.');
        this.invoice.update((i) => (i ? { ...i, status: 'cancelled' } : i));
      },
      error: () => this.actionError.set('No se pudo anular la factura.'),
    });
  }

  goBack(): void {
    void this.router.navigate(['/management/billing/invoices']);
  }

  printPage(): void {
    window.print();
  }

  paymentMethodLabel(method: string): string {
    const map: Record<string, string> = {
      simulated: 'Simulación',
      bank_transfer: 'Transferencia',
      credit_card: 'Tarjeta Crédito',
      cash: 'Efectivo',
      mix: 'Mixto',
    };
    return map[method] ?? method;
  }

  paymentMethodIcon(method: string): string {
    const map: Record<string, string> = {
      simulated: 'payments',
      bank_transfer: 'account_balance',
      credit_card: 'credit_card',
      cash: 'payments',
      mix: 'account_balance',
    };
    return map[method] ?? 'payments';
  }
}

/** Simple number to words converter for Spanish (supports 0-9999). */
function _numToWords(n: number): string {
  if (n === 0) return 'Cero';
  const units = ['', 'Un', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis', 'Siete', 'Ocho', 'Nueve'];
  const teens = ['Diez', 'Once', 'Doce', 'Trece', 'Catorce', 'Quince', 'Dieciséis', 'Diecisiete', 'Dieciocho', 'Diecinueve'];
  const tens = ['', '', 'Veinte', 'Treinta', 'Cuarenta', 'Cincuenta', 'Sesenta', 'Setenta', 'Ochenta', 'Noventa'];
  const hundreds = ['', 'Ciento', 'Doscientos', 'Trescientos', 'Cuatrocientos', 'Quinientos', 'Seiscientos', 'Setecientos', 'Ochocientos', 'Novecientos'];

  let words = '';
  if (n >= 1000) {
    const m = Math.floor(n / 1000);
    words += (m === 1 ? 'Mil' : _numToWords(m) + ' Mil') + ' ';
    n %= 1000;
  }
  if (n >= 100) {
    const c = Math.floor(n / 100);
    words += (c === 1 && n % 100 === 0 ? 'Cien' : hundreds[c]) + ' ';
    n %= 100;
  }
  if (n >= 20) {
    const t = Math.floor(n / 10);
    words += tens[t] + ' ';
    n %= 10;
    if (n > 0) words += 'y ';
  } else if (n >= 10) {
    words += teens[n - 10] + ' ';
    n = 0;
  }
  if (n > 0) {
    words += units[n] + ' ';
  }
  return words.trim();
}
