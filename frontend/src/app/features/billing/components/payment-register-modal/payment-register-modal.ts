import { Component, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface PaymentRegisterPayload {
  booking_id: string;
  invoice_id?: string;
  amount: number;
  method: string;
  status: string;
}

const PAYMENT_METHODS = [
  { id: 'cash', label: 'Efectivo', icon: 'payments' },
  { id: 'card', label: 'Tarjeta', icon: 'credit_card' },
  { id: 'bank_transfer', label: 'Transferencia', icon: 'account_balance' },
  { id: 'simulated', label: 'Tarjeta de crédito', icon: 'credit_card' },
];

const PAYMENT_STATUSES = [
  { id: 'confirmed', label: 'Confirmado', icon: 'check_circle' },
  { id: 'failed', label: 'Fallido', icon: 'cancel' },
  { id: 'rejected', label: 'Rechazado', icon: 'block' },
  { id: 'declined', label: 'Declinado', icon: 'block' },
  { id: 'error', label: 'Error', icon: 'error' },
];

/**
 * Modal para registrar un pago (o un intento fallido/rechazado/declinado/error)
 * contra una reserva. Alimenta `reservation_payments`; el ETL M2C agrega los
 * intentos no confirmados en `kpi_payment_daily.failed_amount` (KPI "Fallidos").
 * Solo los pagos `confirmed` marcan la factura como pagada (lo aplica el server).
 */
@Component({
  selector: 'app-payment-register-modal',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './payment-register-modal.html',
  styleUrl: './payment-register-modal.scss',
})
export class PaymentRegisterModalComponent {
  /** Server error message surfaced by the parent after a failed API call. */
  readonly serverError = input<string | null>(null);
  /** Submit-in-flight flag controlled by the parent. */
  readonly submitting = input(false);

  /** Fires when the user closes the modal (close button or backdrop click). */
  readonly close = output<void>();
  /** Fires when the user confirms; the parent performs the API call. */
  readonly confirmed = output<PaymentRegisterPayload>();

  readonly methods = PAYMENT_METHODS;
  readonly statuses = PAYMENT_STATUSES;

  readonly bookingId = signal('');
  readonly invoiceId = signal('');
  readonly amount = signal<number | null>(null);
  readonly selectedMethod = signal('card');
  readonly selectedStatus = signal('confirmed');
  /** Inline validation messages (distinct from serverError input). */
  readonly localError = signal<string | null>(null);

  selectMethod(method: string): void {
    this.selectedMethod.set(method);
    this.localError.set(null);
  }

  selectStatus(status: string): void {
    this.selectedStatus.set(status);
    this.localError.set(null);
  }

  confirm(): void {
    const bookingId = this.bookingId().trim();
    if (!bookingId) {
      this.localError.set('Ingresa el ID de la reserva.');
      return;
    }
    const amt = this.amount();
    if (!amt || amt <= 0) {
      this.localError.set('Ingresa un monto válido mayor a 0.');
      return;
    }

    this.localError.set(null);
    this.confirmed.emit({
      booking_id: bookingId,
      invoice_id: this.invoiceId().trim() || undefined,
      amount: amt,
      method: this.selectedMethod(),
      status: this.selectedStatus(),
    });
  }
}
