import { CurrencyPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-co-completed-view',
  standalone: true,
  imports: [CurrencyPipe, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="co-checked-out-banner">
      <span class="material-symbols-outlined">check_circle</span>
      Check-out completado &mdash; Folio {{ folio() }}
    </div>

    <div class="co-grid">
      <div class="co-col-main">
        <!-- Guest Info -->
        <div class="co-card">
          <div class="co-card-head"><h2><span class="material-symbols-outlined">person</span> Hu&eacute;sped</h2></div>
          <div class="co-stay-summary">
            <div class="co-stay-row"><span class="co-stay-label">Nombre</span><span class="co-stay-val">{{ guestName() }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label">Documento</span><span class="co-stay-val">{{ cedula() || '&mdash;' }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label">Email</span><span class="co-stay-val">{{ guestEmail() }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label">Tel&eacute;fono</span><span class="co-stay-val">{{ guestPhone() || '&mdash;' }}</span></div>
          </div>
        </div>

        <!-- Stay Details -->
        <div class="co-card">
          <div class="co-card-head"><h2><span class="material-symbols-outlined">meeting_room</span> Estancia</h2></div>
          <div class="co-stay-summary">
            <div class="co-stay-row">
              <span class="co-stay-label"><span class="material-symbols-outlined">meeting_room</span> Habitaci&oacute;n</span>
              <span class="co-stay-val">{{ roomLabel() }}</span>
            </div>
            <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">bed</span> Tipo</span><span class="co-stay-val">{{ roomTypeName() }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">calendar_today</span> Check-In</span><span class="co-stay-val">{{ checkInDate() }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">calendar_today</span> Check-Out</span><span class="co-stay-val">{{ checkOutDate() }}</span></div>
            <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">bed</span> Noches</span><span class="co-stay-val">{{ totalNights() }}</span></div>
            @if (checkOutTimeActual()) {
              <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">schedule</span> Hora salida</span><span class="co-stay-val">{{ checkOutTimeActual() }} hrs</span></div>
            }
            @if (checkOutBy()) {
              <div class="co-stay-row"><span class="co-stay-label"><span class="material-symbols-outlined">badge</span> Atendi&oacute;</span><span class="co-stay-val">{{ checkOutBy() }}</span></div>
            }
          </div>
        </div>

        <!-- Charges -->
        @if (charges().length > 0) {
          <div class="co-card">
            <div class="co-card-head"><h2><span class="material-symbols-outlined">receipt_long</span> Cargos adicionales</h2></div>
            <div class="co-table-wrap">
              <table class="co-table">
                <thead><tr><th>Concepto</th><th>Categor&iacute;a</th><th class="cell-right">Monto</th></tr></thead>
                <tbody>
                  @for (charge of charges(); track charge.concept + charge.created_at) {
                    <tr class="co-table-row">
                      <td>
                        <span class="co-item-name">{{ charge.concept }}</span>
                        @if (charge.note) { <span class="co-item-note">{{ charge.note }}</span> }
                      </td>
                      <td>
                        <span class="material-symbols-outlined co-liq-icon">{{ charge.categoryIcon }}</span>
                        {{ charge.categoryLabel }}
                      </td>
                      <td class="cell-right cell-amount">{{ charge.total | currency:currency() }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- Observations -->
        @if (observations()) {
          <div class="co-card">
            <div class="co-card-head"><h2><span class="material-symbols-outlined">edit_note</span> Observaciones</h2></div>
            <p style="margin:0;font-size:13px;color:var(--text-secondary,#374151);white-space:pre-wrap">{{ observations() }}</p>
          </div>
        }
      </div>

      <div class="co-col-side">
        <!-- Financial Summary -->
        <div class="co-card">
          <div class="co-card-head"><h2><span class="material-symbols-outlined">account_balance</span> Liquidaci&oacute;n</h2></div>
          <div class="co-summary-rows">
            <div class="co-summary-row"><span>Alojamiento</span><span class="co-summary-val">{{ roomTotal() | currency:currency() }}</span></div>
            @if (chargesTotal() > 0) { <div class="co-summary-row"><span>Extras</span><span class="co-summary-val">+ {{ chargesTotal() | currency:currency() }}</span></div> }
            @if (lateFee() > 0) { <div class="co-summary-row"><span>Late Checkout</span><span class="co-summary-val">+ {{ lateFee() | currency:currency() }}</span></div> }
            @if (discountVal() > 0) { <div class="co-summary-row"><span>Descuento{{ discountReason() ? ': ' + discountReason() : '' }}</span><span class="co-summary-val">&minus; {{ discountVal() | currency:currency() }}</span></div> }
            <div class="co-summary-divider"></div>
            <div class="co-summary-row co-summary-grand"><span>TOTAL</span><span class="co-summary-val co-val-grand">{{ grandTotal() | currency:currency() }}</span></div>
            @if (hasPayments()) {
              <div class="co-summary-row"><span>Pagado</span><span class="co-summary-val">&minus; {{ totalPaid() | currency:currency() }}</span></div>
              <div class="co-summary-divider"></div>
            }
            <div class="co-balance-box">
              <span class="co-balance-label">SALDO</span>
              <span class="co-balance-val" [style.color]="balanceDue() <= 0 ? '#065f46' : '#ba1a1a'">
                {{ balanceDue() <= 0 ? 'CANCELADO' : (balanceDue() | currency:currency()) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Payment Method -->
        @if (paymentMethod()) {
          <div class="co-card">
            <div class="co-card-head"><h2><span class="material-symbols-outlined">payments</span> Pago</h2></div>
            <div class="co-stay-summary">
              <div class="co-stay-row">
                <span class="co-stay-label">M&eacute;todo</span>
                <span class="co-stay-val">{{ paymentMethodLabel() }}</span>
              </div>
              @if (paymentRef()) {
                <div class="co-stay-row">
                  <span class="co-stay-label">Referencia</span>
                  <span class="co-stay-val co-ref">{{ paymentRef() }}</span>
                </div>
              }
            </div>
          </div>
        }

        <a routerLink="/management/check-outs" class="co-cta" style="text-decoration:none">
          <span class="material-symbols-outlined">arrow_back</span>
          Volver a check-outs
        </a>
      </div>
    </div>
  `
})
export class CoCompletedViewComponent {
  readonly folio = input('');
  readonly guestName = input('');
  readonly cedula = input('');
  readonly guestEmail = input('');
  readonly guestPhone = input('');
  readonly roomLabel = input('');
  readonly roomTypeName = input('');
  readonly checkInDate = input('');
  readonly checkOutDate = input('');
  readonly totalNights = input(0);
  readonly checkOutTimeActual = input('');
  readonly checkOutBy = input('');
  readonly charges = input<any[]>([]);
  readonly observations = input('');
  readonly roomTotal = input(0);
  readonly chargesTotal = input(0);
  readonly lateFee = input(0);
  readonly discountVal = input(0);
  readonly discountReason = input('');
  readonly grandTotal = input(0);
  readonly hasPayments = input(false);
  readonly totalPaid = input(0);
  readonly balanceDue = input(0);
  readonly currency = input('USD');
  readonly paymentMethod = input('');
  readonly paymentRef = input('');
  readonly paymentMethodLabel = input('');
}
