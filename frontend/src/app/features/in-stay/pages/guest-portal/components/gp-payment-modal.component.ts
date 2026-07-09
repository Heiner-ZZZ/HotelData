import { Component, EventEmitter, Input, Output, signal } from '@angular/core';

@Component({
  selector: 'gp-payment-modal',
  imports: [],
  template: `
    <div class="gp-modal-overlay" (click)="onCancel.emit()">
      <div class="gp-modal" (click)="$event.stopPropagation()">
        <div class="gp-modal-header">
          <span class="material-symbols-outlined gp-modal-icon">
            {{ paymentModalMode() === 'invoice' ? 'receipt_long' : 'payments' }}
          </span>
          <h2>{{ paymentModalMode() === 'invoice' ? 'Solicitar Factura' : 'Solicitar Pago' }}</h2>
        </div>
        <div class="gp-modal-body">
          @if (paymentModalMode() === 'invoice') {
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
          <button class="gp-btn-outline" (click)="onCancel.emit()">Cancelar</button>
          <button class="gp-btn-primary" (click)="onConfirm.emit()" [disabled]="sendingRequest()">
            @if (sendingRequest()) {
              <span class="material-symbols-outlined spin">sync</span>
              Enviando...
            } @else {
              <span class="material-symbols-outlined">send</span>
              {{ paymentModalMode() === 'invoice' ? 'Solicitar Factura' : 'Solicitar Pago' }}
            }
          </button>
        </div>
      </div>
    </div>
  `,
})
export class GpPaymentModalComponent {
  readonly paymentModalMode = signal<'invoice' | 'payment'>('payment');
  readonly sendingRequest = signal(false);

  @Input() set mode(value: 'invoice' | 'payment') { this.paymentModalMode.set(value); }
  @Input() set inputSending(value: boolean) { this.sendingRequest.set(value); }

  @Output() onConfirm = new EventEmitter<void>();
  @Output() onCancel = new EventEmitter<void>();
}
