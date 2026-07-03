import { CurrencyPipe, DatePipe, PercentPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-rd-financial-panels',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, PercentPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm()?.priceBreakdown; as pb) {
      <section class="surface-card panel price-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">receipt_long</span>
            <h2>Desglose de precios</h2>
          </div>
          <span class="panel-badge">{{ pb.source === 'calendar' ? 'Tarifas reales' : 'Estimado' }}</span>
        </div>
        <div class="table-wrap">
          <table class="breakdown-table">
            <thead><tr><th>Fecha</th><th>Tarifa noche</th><th>Habitaciones</th><th class="cell-right">Subtotal</th></tr></thead>
            <tbody>
              @for (night of pb.nights; track night.date) {
                <tr>
                  <td>{{ night.date | date:'dd/MM/yyyy' }}</td>
                  <td>{{ night.rate | currency:pb.currency }}</td>
                  <td>{{ night.rooms }}</td>
                  <td class="cell-right">{{ night.nightTotal | currency:pb.currency }}</td>
                </tr>
              }
            </tbody>
            <tfoot>
              <tr class="foot-subtotal"><td colspan="3">Subtotal</td><td class="cell-right">{{ pb.subtotal | currency:pb.currency }}</td></tr>
              <tr class="foot-taxes"><td colspan="3">IVA ({{ pb.ivaRate | percent }})</td><td class="cell-right">{{ pb.taxes | currency:pb.currency }}</td></tr>
              <tr class="foot-total"><td colspan="3">Total</td><td class="cell-right total-value">{{ pb.total | currency:pb.currency }}</td></tr>
            </tfoot>
          </table>
        </div>
      </section>
    }

    @if ((vm()?.additionalCharges?.length ?? 0) > 0) {
      <section class="surface-card panel charges-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">receipt</span>
            <h2>Cargos por amenities y consumos</h2>
          </div>
          <span class="panel-badge">{{ vm()?.additionalCharges?.length }} cargo(s)</span>
        </div>
        <div class="table-wrap">
          <table class="charges-table">
            <thead>
              <tr><th>Concepto</th><th>Cant.</th><th>Precio</th><th class="cell-right">Total</th></tr>
            </thead>
            <tbody>
              @for (c of vm()?.additionalCharges; track c.createdAt + c.concept) {
                <tr>
                  <td>
                    <strong>{{ c.concept }}</strong>
                    @if (c.note) { <div class="charge-note">{{ c.note }}</div> }
                  </td>
                  <td>{{ c.quantity }}</td>
                  <td>{{ c.amount | currency:'USD' }}</td>
                  <td class="cell-right">{{ c.total | currency:'USD' }}</td>
                </tr>
              }
            </tbody>
            @if ((vm()?.totalCharges ?? 0) > 0) {
              <tfoot>
                <tr class="foot-total">
                  <td colspan="3">Total cargos</td>
                  <td class="cell-right total-value">{{ vm()?.totalCharges | currency:'USD' }}</td>
                </tr>
              </tfoot>
            }
          </table>
        </div>
      </section>
    }

    @if (vm()?.totalPrice !== null) {
      <section class="surface-card panel financial-summary">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">account_balance</span>
            <h2>Resumen financiero</h2>
          </div>
        </div>
        <div class="financial-summary-body">
          <div class="summary-row">
            <span>Habitación ({{ vm()?.totalNights }} {{ vm()?.totalNights === 1 ? 'noche' : 'noches' }})</span>
            <span class="summary-amount">
              @if (vm()?.discountPercent) {
                <span class="summary-original">{{ vm()?.originalTotalPrice | currency:vm()?.currency }}</span>
                {{ vm()?.totalPrice | currency:vm()?.currency }}
              } @else {
                {{ vm()?.totalPrice | currency:vm()?.currency }}
              }
            </span>
          </div>
          @if ((vm()?.additionalCharges?.length ?? 0) > 0) {
            <div class="summary-row summary-row-charges">
              <span>Consumos adicionales ({{ vm()?.additionalCharges?.length }} {{ vm()?.additionalCharges?.length === 1 ? 'cargo' : 'cargos' }})</span>
              <span class="summary-amount">+ {{ vm()?.totalCharges | currency:vm()?.currency }}</span>
            </div>
          }
          <div class="summary-divider-row"></div>
          <div class="summary-row summary-row-total">
            <span>Total</span>
            <span class="summary-amount summary-amount-grand">{{ ((vm()?.totalPrice ?? 0) + (vm()?.totalCharges ?? 0)) | currency:vm()?.currency }}</span>
          </div>
        </div>
      </section>
    }
  `
})
export class RdFinancialPanelsComponent {
  readonly vm = input<any>(null);
}
