import { Component, DestroyRef, EventEmitter, inject, Input, Output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import type { LedgerFolio } from '../../../expenses/models/ledger.model';
import type { FolioPosting, FolioPostingsResponse } from '../../../expenses/models/ledger.model';

const TYPE_LABELS: Record<string, string> = {
  room: 'Habitación',
  charge: 'Cargo',
  discount: 'Descuento',
  payment: 'Pago',
  adjustment: 'Ajuste',
};

const TYPE_ICONS: Record<string, string> = {
  room: 'bed',
  charge: 'add_circle',
  discount: 'sell',
  payment: 'payments',
  adjustment: 'tune',
};

@Component({
  selector: 'app-folio-transactions-modal',
  standalone: true,
  imports: [CurrencyPipe, DatePipe],
  templateUrl: './folio-transactions-modal.html',
  styleUrl: './folio-transactions-modal.scss',
})
export class FolioTransactionsModalComponent {
  private readonly api = inject(ExpensesApiService);
  private readonly destroyRef = inject(DestroyRef);

  @Input() folio: LedgerFolio | null = null;

  @Output() close = new EventEmitter<void>();

  readonly loading = signal(true);
  readonly error = signal('');
  readonly data = signal<FolioPostingsResponse | null>(null);

  ngOnInit(): void {
    const f = this.folio;
    if (!f?.folioId) {
      this.error.set('Folio no encontrado');
      this.loading.set(false);
      return;
    }

    this.api.getFolioPostings(f.folioId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.data.set(res);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Error al cargar transacciones');
          this.loading.set(false);
        },
      });
  }

  typeLabel(type: string): string {
    return TYPE_LABELS[type] || type;
  }

  typeIcon(type: string): string {
    return TYPE_ICONS[type] || 'receipt';
  }

  typeClass(type: string): string {
    switch (type) {
      case 'room':
      case 'charge':
        return 'tx-charge';
      case 'payment':
        return 'tx-payment';
      case 'discount':
      case 'adjustment':
        return 'tx-discount';
      default:
        return '';
    }
  }

  totalByType(postings: FolioPosting[], type: string): number {
    return postings
      .filter(p => p.type === type)
      .reduce((sum, p) => sum + p.amount, 0);
  }
}
