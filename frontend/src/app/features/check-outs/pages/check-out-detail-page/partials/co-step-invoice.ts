import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-invoice',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 4</div>
      <h2 class="co-step-title">Emitir factura</h2>

      <div class="co-invoice-actions">
        <button class="co-inv-btn co-inv-primary">
          <span class="material-symbols-outlined">receipt</span>
          <span class="co-inv-btn-label">Emitir Factura</span>
          <span class="co-inv-btn-sub">Generar CFDI / factura fiscal</span>
        </button>
        <button class="co-inv-btn">
          <span class="material-symbols-outlined">mail</span>
          <span class="co-inv-btn-label">Enviar por Correo</span>
          <span class="co-inv-btn-sub">Al hu&eacute;sped: {{ guestEmail() }}</span>
        </button>
        <button class="co-inv-btn">
          <span class="material-symbols-outlined">print</span>
          <span class="co-inv-btn-label">Imprimir</span>
          <span class="co-inv-btn-sub">Recibo / comprobante</span>
        </button>
      </div>

      <label class="co-check co-split-check" [class.co-checked]="splitInvoice()">
        <input type="checkbox" [ngModel]="splitInvoice()" (ngModelChange)="splitInvoiceChange.emit($event)" />
        <span>Factura separada para consumos</span>
        @if (splitInvoice()) { <span class="co-check-icon material-symbols-outlined">check_circle</span> }
      </label>

      <div class="co-step-actions">
        <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
        <button class="co-btn-primary" (click)="next.emit()">Continuar &rarr;</button>
      </div>
    </section>
  `
})
export class CoStepInvoiceComponent {
  readonly guestEmail = input('');
  readonly splitInvoice = input(false);
  readonly prev = output<void>();
  readonly next = output<void>();
  readonly splitInvoiceChange = output<boolean>();
}
