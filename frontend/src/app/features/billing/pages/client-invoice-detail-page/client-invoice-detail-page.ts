import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { map } from 'rxjs';

import { CurrencyPipe, DatePipe } from '@angular/common';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceDetailViewModel } from '../../models/billing.model';
import { mapInvoiceDetail } from '../../mappers/billing.mapper';
import { BillingApiService } from '../../services/billing-api.service';
import {
  formatCardNumber,
  isCardHolderValid,
  isCvvValid,
  isExpiryValid,
  luhnCheck,
  maskCardNumber,
  maskCardNumberDisplay,
  normalizeCardNumber,
} from './card-form.util';

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
    return id ? `/api/billing/my-invoices/${id}` : undefined;
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
  readonly paymentStep = signal<'idle' | 'card' | 'processing' | 'confirm' | 'done'>('idle');
  readonly paymentReference = signal('');

  /** Saldo pendiente de la factura (total − pagado), para pagos parciales. */
  readonly remainingAmount = computed(() => {
    const inv = this.invoice();
    if (!inv) return 0;
    return Math.max(0, (inv.total ?? 0) - (inv.totalPaidAmount ?? 0));
  });
  /** Monto elegido por el huésped (string del input). Vacío = saldo completo. */
  readonly paymentAmount = signal('');
  /** Monto efectivo a pagar (parseado, default = saldo pendiente). */
  readonly paymentAmountValue = computed(() => {
    const raw = parseFloat(this.paymentAmount());
    return Number.isNaN(raw) || raw <= 0 ? this.remainingAmount() : Math.min(raw, this.remainingAmount());
  });
  readonly paymentAmountError = computed(() => {
    const inv = this.invoice();
    if (!inv) return null;
    const raw = this.paymentAmount().trim();
    if (!raw) return null; // vacío = paga el saldo pendiente
    const num = parseFloat(raw);
    if (Number.isNaN(num) || num <= 0) return 'El monto debe ser mayor a cero.';
    if (num > this.remainingAmount() + 0.001) {
      return `El monto no puede superar el saldo pendiente (${this.remainingAmount().toFixed(2)}).`;
    }
    return null;
  });

  readonly today = signal(new Date().toLocaleDateString('es-MX', {
    year: 'numeric', month: 'long', day: 'numeric',
  }));

  // ── Datos de la tarjeta (pago en línea) ──
  readonly cardNumber = signal('');
  readonly cardHolder = signal('');
  readonly cardExpiry = signal('');
  readonly cardCvv = signal('');
  /** True mientras el campo de número está enmascarado (blur) — el valor
   *  interno ``cardNumber`` SIEMPRE conserva el número completo. */
  readonly cardNumberMasked = signal(false);

  /** Valor mostrado del campo de número: máscara realista (5003 **** ****
   *  7003) al salir del foco, número completo formateado al editarlo. */
  readonly cardNumberDisplay = computed(() =>
    this.cardNumberMasked()
      ? maskCardNumberDisplay(this.cardNumber())
      : formatCardNumber(this.cardNumber()),
  );

  readonly cardNumberError = computed(() => {
    const v = this.cardNumber();
    if (!v) return 'Ingresa el número de tarjeta.';
    if (!luhnCheck(v)) return 'Número de tarjeta inválido.';
    return null;
  });
  readonly cardHolderError = computed(() => {
    const v = this.cardHolder();
    if (!v) return 'Ingresa el nombre del titular.';
    if (!isCardHolderValid(v)) return 'Ingresa el nombre completo del titular.';
    return null;
  });
  readonly cardExpiryError = computed(() => {
    const v = this.cardExpiry();
    if (!v) return 'Ingresa la fecha de vencimiento.';
    if (!isExpiryValid(v)) return 'La tarjeta está vencida o la fecha es inválida.';
    return null;
  });
  readonly cardCvvError = computed(() => {
    const v = this.cardCvv();
    if (!v) return 'Ingresa el CVV.';
    if (!isCvvValid(v)) return 'CVV inválido.';
    return null;
  });
  readonly cardValid = computed(() =>
    !this.cardNumberError() && !this.cardHolderError() && !this.cardExpiryError() && !this.cardCvvError(),
  );
  /** Últimos 4 dígitos enmascarados para la confirmación (nunca el número completo). */
  readonly maskedCard = computed(() => maskCardNumber(this.cardNumber()));

  constructor() {}

  startPayment() {
    // Primer paso: capturar los datos de la tarjeta (número, titular,
    // vencimiento, CVV) — el pago NO puede confirmarse sin ingresarlos.
    this.actionError.set(null);
    this.actionMessage.set(null);
    // Default del monto: saldo pendiente completo (editable para pagos parciales).
    if (!this.paymentAmount()) {
      this.paymentAmount.set(this.remainingAmount().toFixed(2));
    }
    this.paymentStep.set('card');
  }

  onPaymentAmountInput(value: string): void {
    this.paymentAmount.set(value);
  }

  onCardNumberInput(value: string): void {
    // Si el usuario edita un campo que estaba enmascarado (p.ej. autofill sin
    // pasar por focus), descartamos la pulsación y restauramos el número
    // completo para que el siguiente cambio de detección lo re-renderice.
    if (this.cardNumberMasked()) {
      this.cardNumberMasked.set(false);
      return;
    }
    this.cardNumber.set(formatCardNumber(value));
  }

  onCardNumberFocus(): void {
    // Al volver a editar se muestra el número completo.
    this.cardNumberMasked.set(false);
  }

  onCardNumberBlur(): void {
    // Al salir del campo, realismo: el número queda como 5003 **** **** 7003.
    if (normalizeCardNumber(this.cardNumber()).length === 16) {
      this.cardNumberMasked.set(true);
    }
  }

  onCardHolderInput(value: string): void {
    this.cardHolder.set(value);
  }

  onCardExpiryInput(value: string): void {
    const digits = (value || '').replace(/\D/g, '').slice(0, 4);
    this.cardExpiry.set(digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits);
  }

  onCardCvvInput(value: string): void {
    this.cardCvv.set((value || '').replace(/\D/g, '').slice(0, 4));
  }

  submitCard() {
    if (!this.cardValid()) return;
    this.actionError.set(null);
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
    if (!inv || this.paymentAmountError()) return;

    this.paying.set(true);
    this.actionError.set(null);

    this.billingApi.payMyInvoice(inv.id, this.paymentAmountValue()).subscribe({
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
    // Desde la confirmación: volver al formulario para corregir la tarjeta.
    this.paymentStep.set('card');
    this.paying.set(false);
  }

  backToIdle() {
    this.paymentStep.set('idle');
    this.paying.set(false);
  }

  goBack() {
    void this.router.navigate(['/account/billing']);
  }
}
