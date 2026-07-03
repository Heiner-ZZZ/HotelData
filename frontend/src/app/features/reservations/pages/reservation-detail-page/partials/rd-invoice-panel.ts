import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';

@Component({
  selector: 'app-rd-invoice-panel',
  standalone: true,
  imports: [CurrencyPipe, RouterLink, StatusBadgeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm()?.invoice; as inv) {
      <section class="surface-card panel invoice-panel">
        <div class="invoice-panel-header">
          <div class="invoice-panel-title">
            <span class="material-symbols-outlined">receipt_long</span>
            <h2>Facturación</h2>
          </div>
          <app-status-badge
            [tone]="inv.status === 'paid' ? 'success' : inv.status === 'cancelled' ? 'danger' : 'warning'"
            [label]="inv.status === 'paid' ? 'Pagada' : inv.status === 'cancelled' ? 'Anulada' : 'Pendiente de pago'" />
        </div>
        <div class="invoice-summary-grid">
          <div class="inv-info"><span class="inv-label">Factura</span><strong class="inv-value">{{ inv.invoiceNumber }}</strong></div>
          <div class="inv-info"><span class="inv-label">Subtotal</span><strong class="inv-value">{{ inv.subtotal | currency:'USD' }}</strong></div>
          <div class="inv-info"><span class="inv-label">IVA (16%)</span><strong class="inv-value">{{ inv.taxes | currency:'USD' }}</strong></div>
          <div class="inv-info inv-info-total"><span class="inv-label">Total</span><strong class="inv-value">{{ inv.total | currency:'USD' }}</strong></div>
        </div>
        <div class="invoice-actions">
          <button type="button" class="btn-invoice" (click)="goToInvoice.emit(inv.id)">
            <span class="material-symbols-outlined">visibility</span> Ver factura completa
          </button>
          @if (inv.status === 'issued') {
            <a [routerLink]="['/account/billing', inv.id]" class="btn-pay-invoice">
              <span class="material-symbols-outlined">lock</span> Pagar ahora
            </a>
          }
        </div>
      </section>
    }
  `
})
export class RdInvoicePanelComponent {
  readonly vm = input<any>(null);
  readonly goToInvoice = output<string>();
}
