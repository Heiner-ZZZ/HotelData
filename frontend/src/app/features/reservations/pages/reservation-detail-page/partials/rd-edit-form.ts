import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-rd-edit-form',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card panel edit-panel">
      <div class="panel-head">
        <div class="panel-head-left">
          <span class="material-symbols-outlined panel-icon">edit</span>
          <h2>Modificar reserva</h2>
        </div>
      </div>
      @if (editError()) {
        <div class="edit-error">{{ editError() }}</div>
      }
      <div class="edit-form-grid">
        <label class="edit-field">
          <span>Check-in</span>
          <input type="date" [ngModel]="form().checkInDate" (ngModelChange)="onFieldChange('checkInDate', $event)" />
        </label>
        <label class="edit-field">
          <span>Check-out</span>
          <input type="date" [ngModel]="form().checkOutDate" (ngModelChange)="onFieldChange('checkOutDate', $event)" />
        </label>
        <label class="edit-field">
          <span>Habitaciones</span>
          <input type="number" min="1" max="10" [ngModel]="form().rooms" (ngModelChange)="onFieldChange('rooms', Number($event))" />
        </label>
        <label class="edit-field edit-field-wide">
          <span>Comentario</span>
          <input type="text" [ngModel]="form().comment" (ngModelChange)="onFieldChange('comment', $event)" />
        </label>
      </div>
      <div class="edit-actions">
        <button type="button" class="btn-cancel-edit" (click)="cancelEdit.emit()">Cancelar</button>
        <button type="button" class="btn-save-edit" (click)="saveEdit.emit()" [disabled]="editSaving()">
          {{ editSaving() ? 'Guardando...' : 'Guardar cambios' }}
        </button>
      </div>
    </section>
  `
})
export class RdEditFormComponent {
  readonly form = input.required<{ checkInDate: string; checkOutDate: string; rooms: number; comment: string }>();
  readonly editSaving = input(false);
  readonly editError = input<string>('');

  readonly Number = Number;

  readonly cancelEdit = output<void>();
  readonly saveEdit = output<void>();
  readonly fieldChange = output<{ field: 'checkInDate' | 'checkOutDate' | 'rooms' | 'comment'; value: string | number }>();

  onFieldChange(field: 'checkInDate' | 'checkOutDate' | 'rooms' | 'comment', value: string | number): void {
    this.fieldChange.emit({ field, value });
  }
}
