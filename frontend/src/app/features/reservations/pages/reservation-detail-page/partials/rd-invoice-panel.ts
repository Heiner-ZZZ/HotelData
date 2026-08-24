import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';

@Component({
  selector: 'app-rd-invoice-panel',
  standalone: true,
  imports: [CurrencyPipe, RouterLink, StatusBadgeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (noShowPenalty(); as ns) {
      <section class="surface-card panel invoice-panel penalty-panel">
        <div class="invoice-panel-header">
          <div class="invoice-panel-title">
            <span class="material-symbols-outlined">event_busy</span>
            <h2>Penalización por no-show</h2>
          </div>
          <app-status-badge tone="warning" label="Por cobrar" />
        </div>
        <div class="invoice-summary-grid">
          <div class="inv-info inv-info-total">
            <span class="inv-label">Monto a cobrar</span>
            <strong class="inv-value">{{ ns.amount | currency:'USD' }}</strong>
          </div>
          <div class="inv-info"><span class="inv-label">Penalización</span><strong class="inv-value">{{ ns.percent }}% de 1 noche</strong></div>
          @if (ns.folioNumber) {
            <div class="inv-info"><span class="inv-label">Folio</span><strong class="inv-value inv-value-mono">{{ ns.folioNumber }}</strong></div>
          }
        </div>
        <p class="penalty-note">
          El huésped no se presentó: se cobra la penalización de la primera noche
          y la estadía completa no aplica. La factura queda como referencia en
          Facturación.
        </p>
      </section>
    } @else if (vm()?.invoice; as inv) {
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

  /** Penalización del no-show: la fuente de verdad del importe a cobrar.
   *  Cuando el huésped no se presentó, el panel NO presenta la factura de la
   *  estadía como "pendiente de pago" (sería engañoso y permitiría pagar
   *  $188 cuando lo que corresponde son $47.94 de penalización). */
  readonly noShowPenalty = computed(() => {
    const v = this.vm();
    if (!v || v.stayStatus !== 'no_show') return null;
    const amount = Number(v.noShowPenaltyAmount ?? 0);
    if (!(amount > 0)) return null;
    return {
      amount,
      percent: Number(v.noShowPenaltyPercent ?? 0),
      folioNumber: v.noShowFolioNumber ?? null,
    };
  });
}
