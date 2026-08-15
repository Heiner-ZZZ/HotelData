import { CurrencyPipe } from '@angular/common';
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

      @if (reconcileNote(); as note) {
        <div class="co-liq-reconcile" role="note" aria-live="polite">
          <span class="material-symbols-outlined">fact_check</span>
          <div>
            <strong>La factura no cubre los cargos adicionales</strong>
            <span>
              La factura {{ note.invoice_number }} se emiti&oacute; antes de los &uacute;ltimos cargos:
              faltan <strong>{{ note.gap | currency:currency() }}</strong> &mdash; el TOTAL incluye los cargos nuevos.
            </span>
          </div>
        </div>
      }

      <div class="co-liq-summary">
        <div class="co-liq-row"><span>Subtotal</span><span class="co-liq-val">{{ subtotal() | currency:currency() }}</span></div>
        <div class="co-liq-row co-liq-tax"><span>IVA (16%)</span><span class="co-liq-val">{{ taxes() | currency:currency() }}</span></div>
        <div class="co-liq-divider"></div>
        <div class="co-liq-row co-liq-grand"><span>TOTAL</span><span class="co-liq-val">{{ grandTotal() | currency:currency() }}</span></div>
        @if (totalPaid() > 0) { <div class="co-liq-row co-liq-paid"><span>Pagado</span><span class="co-liq-val">&minus; {{ totalPaid() | currency:currency() }}</span></div> }
        <div class="co-liq-divider"></div>
        <div class="co-liq-row co-liq-balance"><span>SALDO</span><span class="co-liq-val">{{ balanceDue() | currency:currency() }}</span></div>
      </div>

      <!-- Late check-out: ventana gobernada por la política del hotel -->
      @if (lateContext(); as lc) {
        @if (lc.is_late) {
          <div class="co-late-panel" [class.co-late-panel--blocked]="lateBlocked()">
            <div class="co-late-head">
              <span class="material-symbols-outlined">schedule</span>
              <strong>Late check-out</strong>
              <span class="co-late-minutes">+{{ lc.minutes_after }} min tras las {{ lc.check_out_time }}</span>
            </div>
            @if (lc.real_time) {
              <div class="co-late-real">
                <span class="material-symbols-outlined">schedule</span>
                Salida real: <strong>{{ lc.real_time }} hrs</strong>
                <span class="co-late-real-note">(hora actual del hotel)</span>
              </div>
            }
            @if (!lc.requires_approval) {
              <div class="co-late-courtesy">
                <span class="material-symbols-outlined">verified</span>
                Dentro de la cortes&iacute;a ({{ lc.courtesy_minutes }} min) &mdash; salida tard&iacute;a sin cargo
              </div>
            } @else if (canApproveLate()) {
              <div class="co-late-approve">
                <label class="co-label">Autorizar salida tard&iacute;a</label>
                <select class="co-select" [ngModel]="lateMode()" (ngModelChange)="lateModeChange.emit($event)">
                  <option value="">Sin autorizar</option>
                  <option value="late_approved">Aprobar con cargo</option>
                </select>
                @if (lateMode() === 'late_approved') {
                  <label class="co-label">Motivo (requerido)</label>
                  <textarea class="co-textarea" rows="2" [ngModel]="lateReason()" (ngModelChange)="lateReasonChange.emit($event)" placeholder="Motivo de la aprobaci&oacute;n..."></textarea>
                  <label class="co-label">Cargo por late check-out ($)</label>
                  <input type="number" class="co-input" min="0" step="0.01" [ngModel]="lateFee()" (ngModelChange)="lateFeeChange.emit($event)" />
                }
              </div>
            } @else {
              <div class="co-late-alert" role="alert" aria-live="polite">
                <span class="material-symbols-outlined">lock</span>
                Esta salida supera la cortes&iacute;a ({{ lc.courtesy_minutes }} min) y requiere aprobaci&oacute;n del gerente (permiso <code>check-ins.late_checkout_approve</code>).
                Derivalo al gerente para que autorice la salida extendida antes de completar.
              </div>
            }
          </div>
        }
      }

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
  /** Nota de reconciliación cuando la factura emitida no cubre los cargos adicionales. */
  readonly reconcileNote = input<{ invoice_number: string; gap: number } | null>(null);
  readonly subtotal = input(0);
  readonly taxes = input(0);
  readonly grandTotal = input(0);
  readonly totalPaid = input(0);
  readonly balanceDue = input(0);
  readonly currency = input('USD');
  readonly paymentMethod = input('credit_card');
  readonly paymentRef = input('');
  readonly lateContext = input<{
    enabled: boolean;
    is_late: boolean;
    minutes_after: number;
    courtesy_minutes: number;
    requires_approval: boolean;
    check_out_time: string;
    default_fee: number;
    real_time: string;
  } | null>(null);
  readonly canApproveLate = input(false);
  readonly lateMode = input<string>('');
  readonly lateReason = input<string>('');
  readonly lateBlocked = input(false);

  readonly prev = output<void>();
  readonly next = output<void>();
  readonly paymentMethodChange = output<string>();
  readonly paymentRefChange = output<string>();
  readonly lateModeChange = output<string>();
  readonly lateReasonChange = output<string>();
  readonly lateFeeChange = output<number>();
}
