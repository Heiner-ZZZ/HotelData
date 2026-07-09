import { Component, EventEmitter, Input, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'gp-confirm-modal',
  imports: [FormsModule],
  template: `
    <div class="gp-modal-overlay" (click)="onCancel.emit()">
      <div class="gp-modal" (click)="$event.stopPropagation()">
        <div class="gp-modal-header">
          <span class="material-symbols-outlined gp-modal-icon">help</span>
          <h2>{{ title() }}</h2>
        </div>
        <div class="gp-modal-body">
          @if (dndWarning()) {
            <div class="gp-modal-dnd-warning">
              <span class="material-symbols-outlined">do_not_disturb</span>
              <p>Tienes el modo <strong>No Molestar</strong> activado. Se desactivará automáticamente al enviar esta solicitud.</p>
            </div>
          }
          <p>{{ message() }}</p>
          @if (showExtendFields()) {
            <div class="gp-extend-form">
              @if (confirmActionType() === 'extend_stay') {
                <label>Nueva fecha de salida</label>
                <input type="date" [ngModel]="extendDate()" (ngModelChange)="extendDate.set($event)" [min]="minCheckOut" />
              }
              @if (confirmActionType() === 'late_checkout') {
                <label>Hora de salida deseada</label>
                <input type="time" [ngModel]="extendTime()" (ngModelChange)="extendTime.set($event)" />
              }
            </div>
          }
        </div>
        <div class="gp-modal-footer">
          <button class="gp-btn-outline" (click)="onCancel.emit()">Cancelar</button>
          <button class="gp-btn-primary" (click)="onConfirm.emit()" [disabled]="confirmDisabled">
            @if (sendingRequest()) {
              <span class="material-symbols-outlined spin">sync</span>
              Enviando...
            } @else {
              Confirmar
            }
          </button>
        </div>
      </div>
    </div>
  `,
})
export class GpConfirmModalComponent {
  readonly title = signal('');
  readonly message = signal('');
  readonly dndWarning = signal(false);
  readonly showExtendFields = signal(false);
  readonly confirmActionType = signal('');
  readonly extendDate = signal('');
  readonly extendTime = signal('');
  readonly sendingRequest = signal(false);

  @Input() set inputTitle(value: string) { this.title.set(value); }
  @Input() set inputMessage(value: string) { this.message.set(value); }
  @Input() set inputDndWarning(value: boolean) { this.dndWarning.set(value); }
  @Input() set inputShowExtend(value: boolean) { this.showExtendFields.set(value); }
  @Input() set inputActionType(value: string) { this.confirmActionType.set(value); }
  @Input() set inputExtendDate(value: string) { this.extendDate.set(value); }
  @Input() set inputExtendTime(value: string) { this.extendTime.set(value); }
  @Input() set inputSending(value: boolean) { this.sendingRequest.set(value); }
  @Input() minCheckOut = '';
  @Input() confirmDisabled = false;

  @Output() onConfirm = new EventEmitter<void>();
  @Output() onCancel = new EventEmitter<void>();
}
