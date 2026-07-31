import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CurrencyPipe } from '@angular/common';
import type { LedgerFolio } from '../../../expenses/models/ledger.model';

type ModalMode = 'payment' | 'transfer';

const PAYMENT_METHODS = [
  { id: 'cash', label: 'Efectivo', icon: 'payments' },
  { id: 'card', label: 'Tarjeta', icon: 'credit_card' },
  { id: 'transfer', label: 'Transferencia', icon: 'account_balance' },
  { id: 'other', label: 'Otro', icon: 'more_horiz' },
];

@Component({
  selector: 'app-folio-payment-modal',
  standalone: true,
  imports: [FormsModule, CurrencyPipe],
  templateUrl: './folio-payment-modal.html',
  styleUrl: './folio-payment-modal.scss',
})
export class FolioPaymentModalComponent {
  /** 'payment' shows method picker + folio balance guard; 'transfer' shows target-folio picker. */
  readonly mode = input<ModalMode>('payment');
  /** Folio being paid into (or transferred FROM in transfer mode). */
  readonly folio = input<LedgerFolio | null>(null);
  /** Other open folios available as transfer targets (only used when mode === 'transfer'). */
  readonly availableFolios = input<LedgerFolio[]>([]);
  /**
   * Server error message surfaced by the parent after a failed API call.
   * Parent is responsible for clearing its own ``submitting`` flag — the
   * modal is purely presentational.
   */
  readonly serverError = input<string | null>(null);

  /** Fires when the user closes the modal (close button or backdrop click). */
  readonly close = output<void>();
  /** Fires when the user clicks Confirmar; parent performs the actual API call. */
  readonly confirmed = output<{
    amount: number;
    method?: string;
    notes: string;
    targetFolioId?: string;
  }>();

  readonly methods = PAYMENT_METHODS;

  readonly amount = signal<number | null>(null);
  readonly selectedMethod = signal('cash');
  readonly targetFolioId = signal('');
  readonly notes = signal('');
  /** Local "submit in flight" flag — controls Confirm/Espinar button disabled state and spinner. */
  readonly submitting = signal(false);
  /** Inline validation messages (empty string by default). Distinct from serverError input. */
  readonly localError = signal<string | null>(null);

  selectMethod(method: string): void {
    this.selectedMethod.set(method);
    this.localError.set(null);
  }

  /** Derived title from mode — replaces the legacy getter. */
  readonly title = computed(() => this.mode() === 'payment' ? 'Registrar Pago' : 'Transferir Cargos');

  /**
   * Derived list of transfer-target folios. Excludes the source folio and
   * only includes folios currently open. Replaces the legacy getter.
   */
  readonly targetFolios = computed(() =>
    this.availableFolios().filter(f => f.folioId !== this.folio()?.folioId && f.status === 'open')
  );

  confirm(): void {
    const amt = this.amount();
    if (!amt || amt <= 0) {
      this.localError.set('Ingresa un monto válido mayor a 0.');
      return;
    }

    if (this.mode() === 'transfer' && !this.targetFolioId()) {
      this.localError.set('Selecciona un folio destino.');
      return;
    }

    const folioBalance = this.folio()?.balance ?? 0;
    if (this.mode() === 'payment' && amt > folioBalance) {
      this.localError.set(`El monto excede el saldo pendiente (${folioBalance})`);
      return;
    }

    if (this.mode() === 'transfer') {
      const target = this.targetFolios().find(f => f.folioId === this.targetFolioId());
      if (!target) {
        this.localError.set('Folio destino no encontrado.');
        return;
      }
    }

    this.localError.set(null);
    this.submitting.set(true);

    this.confirmed.emit({
      amount: amt,
      method: this.mode() === 'payment' ? this.selectedMethod() : undefined,
      notes: this.notes(),
      targetFolioId: this.mode() === 'transfer' ? this.targetFolioId() : undefined,
    });
  }
}
