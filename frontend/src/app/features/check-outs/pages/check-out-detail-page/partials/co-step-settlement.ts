import { CurrencyPipe, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-settlement',
  standalone: true,
  imports: [CurrencyPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 3</div>
      <h2 class="co-step-title">Liquidaci&oacute;n</h2>

      <div class="co-liq-table-wrap">
        <table class="co-liq-table">
          <thead><tr><th>Concepto</th><th class="cell-right">Monto</th></tr></thead>
          <tbody>
            <tr><td>Alojamiento ({{ totalNights() }} noches)</td><td class="cell-right">{{ roomTotal() | currency:currency() }}</td></tr>
            @for (catEntry of chargesByCategory(); track catEntry.key) {
              @if (catEntry.items.length) {
                <tr><td><span class="material-symbols-outlined co-liq-icon">{{ catEntry.icon }}</span> {{ catEntry.label }}</td><td class="cell-right">+ {{ catEntry.total | currency:currency() }}</td></tr>
              }
            }
            @if (lateFee() > 0) { <tr class="co-row-late"><td><span class="material-symbols-outlined co-liq-icon">schedule</span> Late Checkout</td><td class="cell-right">+ {{ lateFee() | currency:currency() }}</td></tr> }
            @if (discountVal() > 0) { <tr class="co-row-discount"><td><span class="material-symbols-outlined co-liq-icon">percent</span> Descuento{{ discountReason() ? ': ' + discountReason() : '' }}</td><td class="cell-right">&minus; {{ discountVal() | currency:currency() }}</td></tr> }
          </tbody>
        </table>
      </div>

      <div class="co-liq-summary">
        <div class="co-liq-row"><span>Subtotal</span><span class="co-liq-val">{{ subtotal() | currency:currency() }}</span></div>
        <div class="co-liq-row co-liq-tax"><span>IVA (16%)</span><span class="co-liq-val">{{ taxes() | currency:currency() }}</span></div>
        <div class="co-liq-divider"></div>
        <div class="co-liq-row co-liq-grand"><span>TOTAL</span><span class="co-liq-val">{{ grandTotal() | currency:currency() }}</span></div>
        @if (totalPaid() > 0) { <div class="co-liq-row co-liq-paid"><span>Pagado</span><span class="co-liq-val">&minus; {{ totalPaid() | currency:currency() }}</span></div> }
        <div class="co-liq-divider"></div>
        <div class="co-liq-row co-liq-balance"><span>SALDO</span><span class="co-liq-val">{{ balanceDue() | currency:currency() }}</span></div>
      </div>

      <!-- Payment method inline -->
      <div class="co-liq-payment">
        <span class="co-label">Forma de pago</span>
        <div class="co-liq-pay-row">
          <select class="co-select" [ngModel]="paymentMethod()" (ngModelChange)="paymentMethodChange.emit($event)">
            <option value="credit_card">Tarjeta Cr&eacute;dito / D&eacute;bito</option>
            <option value="cash">Efectivo (Caja Principal)</option>
            <option value="transfer">Transferencia Bancaria</option>
            <option value="mixed">Pago Mixto</option>
          </select>
          <input type="text" class="co-input" placeholder="Referencia"
            [ngModel]="paymentRef()" (ngModelChange)="paymentRefChange.emit($event)" />
        </div>
      </div>

      <div class="co-step-actions">
        <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
        <button class="co-btn-primary" (click)="next.emit()">Continuar &rarr;</button>
      </div>
    </section>
  `
})
export class CoStepSettlementComponent {
  readonly totalNights = input(0);
  readonly roomTotal = input(0);
  readonly chargesByCategory = input<any[]>([]);
  readonly lateFee = input(0);
  readonly discountVal = input(0);
  readonly discountReason = input('');
  readonly subtotal = input(0);
  readonly taxes = input(0);
  readonly grandTotal = input(0);
  readonly totalPaid = input(0);
  readonly balanceDue = input(0);
  readonly currency = input('USD');
  readonly paymentMethod = input('credit_card');
  readonly paymentRef = input('');

  readonly prev = output<void>();
  readonly next = output<void>();
  readonly paymentMethodChange = output<string>();
  readonly paymentRefChange = output<string>();
}
