import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-summary',
  standalone: true,
  imports: [CurrencyPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 1</div>
      <h2 class="co-step-title">Resumen de estancia</h2>

      <div class="co-stay-summary">
        <div class="co-stay-row">
          <span class="co-stay-label"><span class="material-symbols-outlined">meeting_room</span> Habitación</span>
          <span class="co-stay-val">{{ roomLabel() }} &mdash; {{ roomTypeName() }}</span>
        </div>
        <div class="co-stay-row">
          <span class="co-stay-label"><span class="material-symbols-outlined">bed</span> Noches</span>
          <span class="co-stay-val">{{ totalNights() }}</span>
        </div>
        <div class="co-stay-row">
          <span class="co-stay-label"><span class="material-symbols-outlined">attach_money</span> Tarifa por noche</span>
          <span class="co-stay-val">{{ nightRate() | currency:currency() }}</span>
        </div>
        <div class="co-stay-row">
          <span class="co-stay-label"><span class="material-symbols-outlined">receipt_long</span> Extras</span>
          <span class="co-stay-val">{{ chargesTotal() | currency:currency() }}</span>
        </div>
        @if (hasPayments()) {
          <div class="co-stay-row">
            <span class="co-stay-label"><span class="material-symbols-outlined">payments</span> Pagado</span>
            <span class="co-stay-val co-stay-paid">{{ totalPaid() | currency:currency() }}</span>
          </div>
        }
        <div class="co-stay-divider"></div>
        <div class="co-stay-row co-stay-row-balance">
          <span class="co-stay-label"><span class="material-symbols-outlined">account_balance</span> Pendiente</span>
          <span class="co-stay-val co-stay-pending">{{ balanceDue() | currency:currency() }}</span>
        </div>
      </div>

      <div class="co-confirm-box">
        <p class="co-confirm-question">&iquest;Todo es correcto?</p>
        <div class="co-confirm-btns">
          <button class="co-btn-confirm co-btn-si" [class.selected]="everythingCorrect() === true" (click)="setCorrect.emit(true)">
            <span class="material-symbols-outlined">check_circle</span> S&iacute;, continuar
          </button>
          <button class="co-btn-confirm co-btn-no" [class.selected]="everythingCorrect() === false" (click)="setCorrect.emit(false)">
            <span class="material-symbols-outlined">edit</span> No, agregar cargos
          </button>
        </div>
      </div>
    </section>
  `
})
export class CoStepSummaryComponent {
  readonly roomLabel = input<string>('');
  readonly roomTypeName = input<string>('');
  readonly totalNights = input(0);
  readonly nightRate = input(0);
  readonly chargesTotal = input(0);
  readonly hasPayments = input(false);
  readonly totalPaid = input(0);
  readonly balanceDue = input(0);
  readonly currency = input('USD');
  readonly everythingCorrect = input<boolean | null>(null);
  readonly setCorrect = output<boolean>();
}
