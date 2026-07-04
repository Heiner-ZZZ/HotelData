import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
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
  @Input() mode: ModalMode = 'payment';
  @Input() folio: LedgerFolio | null = null;
  @Input() availableFolios: LedgerFolio[] = [];

  /** Server error from parent (set via property binding after failed API call) */
  @Input()
  set serverError(value: string | null) {
    if (value) {
      this.submitting.set(false);
      this._serverError.set(value);
    }
  }
  get serverError(): string | null {
    return this._serverError();
  }
  private readonly _serverError = signal<string | null>(null);

  @Output() close = new EventEmitter<void>();
  @Output() confirmed = new EventEmitter<{
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
  readonly submitting = signal(false);

  selectMethod(method: string): void {
    this.selectedMethod.set(method);
  }

  confirm(): void {
    const amt = this.amount();
    if (!amt || amt <= 0) {
      this._serverError.set('Ingresa un monto válido mayor a 0.');
      return;
    }

    if (this.mode === 'transfer' && !this.targetFolioId()) {
      this._serverError.set('Selecciona un folio destino.');
      return;
    }

    if (this.mode === 'payment' && amt > (this.folio?.balance ?? 0)) {
      this._serverError.set(`El monto excede el saldo pendiente (${this.folio?.balance})`);
      return;
    }

    if (this.mode === 'transfer') {
      const target = this.availableFolios.find(f => f.folioId === this.targetFolioId());
      if (!target) {
        this._serverError.set('Folio destino no encontrado.');
        return;
      }
    }

    this._serverError.set(null);
    this.submitting.set(true);

    this.confirmed.emit({
      amount: amt,
      method: this.mode === 'payment' ? this.selectedMethod() : undefined,
      notes: this.notes(),
      targetFolioId: this.mode === 'transfer' ? this.targetFolioId() : undefined,
    });
  }

  get title(): string {
    return this.mode === 'payment' ? 'Registrar Pago' : 'Transferir Cargos';
  }

  get targetFolios(): LedgerFolio[] {
    return this.availableFolios.filter(f => f.folioId !== this.folio?.folioId && f.status === 'open');
  }
}
