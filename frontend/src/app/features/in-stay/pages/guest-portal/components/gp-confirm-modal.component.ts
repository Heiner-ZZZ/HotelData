import { Component, input, linkedSignal, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'gp-confirm-modal',
  imports: [FormsModule],
  template: `
    <div class="gp-modal-overlay" (click)="cancelled.emit()">
      <div class="gp-modal" (click)="$event.stopPropagation()">
        <div class="gp-modal-header">
          <span class="material-symbols-outlined gp-modal-icon">help</span>
          <h2>{{ inputTitle() }}</h2>
        </div>
        <div class="gp-modal-body">
          @if (inputDndWarning()) {
            <div class="gp-modal-dnd-warning">
              <span class="material-symbols-outlined">do_not_disturb</span>
              <p>Tienes el modo <strong>No Molestar</strong> activado. Se desactivará automáticamente al enviar esta solicitud.</p>
            </div>
          }
          <p>{{ inputMessage() }}</p>
          @if (inputShowExtend()) {
            <div class="gp-extend-form">
              @if (inputActionType() === 'extend_stay') {
                <label>Nueva fecha de salida</label>
                <input type="date" [ngModel]="extendDate()" (ngModelChange)="extendDate.set($event)" [min]="minCheckOut()" />
              }
              @if (inputActionType() === 'late_checkout') {
                <label>Hora de salida deseada</label>
                <input type="time" [ngModel]="extendTime()" (ngModelChange)="extendTime.set($event)" />
              }
            </div>
          }
        </div>
        <div class="gp-modal-footer">
          <button class="gp-btn-outline" (click)="cancelled.emit()">Cancelar</button>
          <button class="gp-btn-primary" (click)="confirmed.emit()" [disabled]="confirmDisabled()">
            @if (inputSending()) {
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
  /** Modal title (italic Spanish label, e.g. "Solicitar extensión de estancia"). */
  readonly inputTitle = input('');
  /** Long-form body message displayed under the title. */
  readonly inputMessage = input('');
  /** When true, show the "Do Not Disturb will be disabled" banner. */
  readonly inputDndWarning = input(false);
  /** When true, render the extend-date/extend-time fields. */
  readonly inputShowExtend = input(false);
  /** 'extend_stay' renders date input; 'late_checkout' renders time input; any other value renders none. */
  readonly inputActionType = input('');
  /** Pre-filled date for extend_stay — seed for the ``extendDate`` linkedSignal below. */
  readonly inputExtendDate = input('');
  /** Pre-filled time for late_checkout — seed for the ``extendTime`` linkedSignal below. */
  readonly inputExtendTime = input('');
  /**
   * Writable mirror of ``inputExtendDate`` so the template's
   * ``[ngModel]`` + ``(ngModelChange)`` can drive the date input. Uses
   * ``linkedSignal`` instead of ``effect + signal``: the linkedSignal source
   * re-evaluates automatically when ``inputExtendDate()`` changes, while
   * still allowing local ``.set()`` overrides from ngModel. Avoids the
   * Angular 22 NG0600 trap (effects writing other signals require explicit
   * ``{ allowSignalWrites: true }`` opt-in).
   */
  readonly extendDate = linkedSignal(() => this.inputExtendDate() || '');
  /** Writable mirror of ``inputExtendTime`` — see ``extendDate`` for rationale. */
  readonly extendTime = linkedSignal(() => this.inputExtendTime() || '');
  /** True while the parent is mid-flight so the submit button shows "Enviando..." and is disabled. */
  readonly inputSending = input(false);
  /** Lower bound for the extend-stay date picker (existing check-out date). */
  readonly minCheckOut = input('');
  /** Disables the Confirm button when the parent has a reason to block submission. */
  readonly confirmDisabled = input(false);

  /** Fires when the user clicks Confirmar. Parent performs the actual API call. */
  readonly confirmed = output<void>();
  /** Fires when the user clicks Cancelar or the backdrop. */
  readonly cancelled = output<void>();
}
