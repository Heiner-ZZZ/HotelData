import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-rp-delete-modal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="modal-overlay" (click)="cancel.emit()">
      <div class="modal-panel confirm-panel" (click)="$event.stopPropagation()">
        <div class="modal-head">
          <span class="material-symbols-outlined modal-head-icon" style="color: var(--danger)">warning</span>
          <div>
            <h2>¿Eliminar tipo de habitación?</h2>
            <p>{{ targetName() }} ({{ targetId() }})</p>
          </div>
          <button type="button" class="modal-close" (click)="cancel.emit()" aria-label="Cerrar">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <div class="modal-body">
          <p class="confirm-text">
            Se eliminará el tipo de habitación, sus habitaciones físicas y el inventario asociado.
            Esta acción no se puede deshacer.
          </p>
          @if (errorMessage()) {
            <div class="toast toast-error" style="margin-bottom: 0.75rem;">
              <span class="material-symbols-outlined">error</span>
              {{ errorMessage() }}
            </div>
          }
          <div class="modal-actions">
            <button type="button" class="btn-secondary" (click)="cancel.emit()" [disabled]="deleting()">Cancelar</button>
            <button type="button" class="btn-danger" (click)="confirm.emit()" [disabled]="deleting()">
              @if (deleting()) {
                <span class="material-symbols-outlined spin">progress_activity</span>
              } @else {
                <span class="material-symbols-outlined">delete</span>
              }
              Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>
  `
})
export class RpDeleteModalComponent {
  readonly targetName = input('');
  readonly targetId = input('');
  readonly errorMessage = input('');
  readonly deleting = input(false);
  readonly cancel = output<void>();
  readonly confirm = output<void>();
}
