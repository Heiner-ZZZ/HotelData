import { Component, input, output } from '@angular/core';

@Component({
  selector: 'gp-payment-modal',
  imports: [],
  template: `
    <div class="gp-modal-overlay" (click)="cancelled.emit()">
      <div class="gp-modal" (click)="$event.stopPropagation()">
        <div class="gp-modal-header">
          <span class="material-symbols-outlined gp-modal-icon">
            {{ mode() === 'invoice' ? 'receipt_long' : 'payments' }}
          </span>
          <h2>{{ mode() === 'invoice' ? 'Solicitar Factura' : 'Solicitar Pago' }}</h2>
        </div>
        <div class="gp-modal-body">
          @if (mode() === 'invoice') {
            <p>Se notificará a recepción que deseas recibir la factura detallada de tu estancia. Un miembro del staff te contactará para entregártela.</p>
          } @else {
            <p>Puedes solicitar realizar un pago parcial o total de tu folio. Recepción recibirá tu solicitud y te contactará para procesar el pago.</p>
          }
          <div class="gp-modal-info">
            <span class="material-symbols-outlined">info</span>
            <span>También puedes acercarte a recepción directamente.</span>
          </div>
        </div>
        <div class="gp-modal-footer">
          <button class="gp-btn-outline" (click)="cancelled.emit()">Cancelar</button>
          <button class="gp-btn-primary" (click)="confirmed.emit()" [disabled]="inputSending()">
            @if (inputSending()) {
              <span class="material-symbols-outlined spin">sync</span>
              Enviando...
            } @else {
              <span class="material-symbols-outlined">send</span>
              {{ mode() === 'invoice' ? 'Solicitar Factura' : 'Solicitar Pago' }}
            }
          </button>
        </div>
      </div>
    </div>
  `,
})
export class GpPaymentModalComponent {
  /** Whether the modal is asking for an invoice or a payment. Defaults to 'payment'. */
  readonly mode = input<'invoice' | 'payment'>('payment');
  /** Set by parent during the in-flight request to disable the submit button. */
  readonly inputSending = input(false);

  /** Fires when the user clicks the primary action ("Solicitar Factura" / "Solicitar Pago"). */
  readonly confirmed = output<void>();
  /** Fires when the user clicks Cancelar or the backdrop. */
  readonly cancelled = output<void>();
}
