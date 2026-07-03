import { ReactiveFormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { AiSuggestDirective } from '../../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-rp-create-form',
  standalone: true,
  imports: [ReactiveFormsModule, AiSuggestDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card form-panel">
      <div class="panel-head">
        <span class="material-symbols-outlined panel-head-icon icon-create-green">king_bed</span>
        <div>
          <h2>Nuevo tipo de habitación</h2>
          <p>Crea un tipo de habitación operativo para inventario y disponibilidad.</p>
        </div>
      </div>
      <form [formGroup]="createForm()" (submit)="$event.preventDefault(); createRoomType.emit()" class="form-grid">
        <!-- Toggle: select existing vs create new -->
        <div class="create-mode-toggle" style="grid-column: 1 / -1">
          <button type="button" class="toggle-mode-btn" [class.is-active]="createMode() === 'existing'" (click)="setMode.emit('existing')">
            <span class="material-symbols-outlined">list_alt</span>
            Usar existente
          </button>
          <button type="button" class="toggle-mode-btn" [class.is-active]="createMode() === 'new'" (click)="setMode.emit('new')">
            <span class="material-symbols-outlined">add_circle</span>
            Crear nuevo
          </button>
        </div>

        @if (createMode() === 'existing') {
          <label class="field" style="grid-column: 1 / -1">
            <span class="field-label">
              <span class="material-symbols-outlined field-icon">bed</span>
              Tipo existente
            </span>
            <select [value]="selectedExistingId()" (change)="selectExisting.emit($any($event.target).value)">
              <option value="">Seleccionar tipo de habitación…</option>
              @for (rt of existingRoomTypes(); track rt.id) {
                <option [value]="rt.id">{{ rt.name }}</option>
              }
            </select>
          </label>
          @if (selectedExistingId()) {
            <div class="existing-type-info" style="grid-column: 1 / -1">
              <span class="material-symbols-outlined">info</span>
              <span>Se copiarán los datos del tipo seleccionado. Solo agrega el número de habitación y piso.</span>
            </div>
          }
        }

        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">badge</span>
            Nombre
          </span>
          <input formControlName="name" placeholder="Ej: Suite Premium" [class.readonly-field]="createMode() === 'existing'" [attr.readonly]="createMode() === 'existing' || null">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">description</span>
            Descripción
          </span>
          <textarea rows="3" formControlName="description" placeholder="Opcional" appAiSuggest="descripcion_habitacion"></textarea>
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">tag</span>
            N° Habitación
          </span>
          <input formControlName="roomNumber" placeholder="Ej: 101">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">floor</span>
            Piso / PB
          </span>
          <input formControlName="floor" placeholder="Ej: 1, 2, PB">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">group</span>
            Adultos máx.
          </span>
          <input type="number" min="1" formControlName="maxAdults">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">child_care</span>
            Niños máx.
          </span>
          <input type="number" min="0" formControlName="maxChildren">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">people</span>
            Capacidad base
          </span>
          <input type="number" min="1" formControlName="baseCapacity">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">attach_money</span>
            Tarifa base ($/noche)
          </span>
          <input type="number" min="0" step="0.01" formControlName="baseRate" placeholder="0 = sin tarifa base">
        </label>
        <label class="field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">landscape</span>
            Vista
          </span>
          <select formControlName="view">
            <option value="">Seleccionar…</option>
            <option value="Mar">Mar</option>
            <option value="Ciudad">Ciudad</option>
            <option value="Jardín">Jardín</option>
            <option value="Montaña">Montaña</option>
            <option value="Piscina">Piscina</option>
            <option value="Patio interior">Patio interior</option>
          </select>
        </label>
        <label class="field checkbox-field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">smoking_rooms</span>
            Fumador
          </span>
          <input type="checkbox" formControlName="smoking">
        </label>
        <label class="field checkbox-field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">accessible</span>
            Accesible
          </span>
          <input type="checkbox" formControlName="accessible">
        </label>
        <label class="field checkbox-field">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">toggle_on</span>
            Activo
          </span>
          <input type="checkbox" formControlName="isActive">
        </label>
        <div class="form-actions">
          <button type="submit" class="btn-primary">
            <span class="material-symbols-outlined btn-icon">add</span>
            Crear tipo
          </button>
        </div>
      </form>
    </section>
  `
})
export class RpCreateFormComponent {
  readonly createForm = input<any>(null);
  readonly createMode = input<string>('new');
  readonly existingRoomTypes = input<any[]>([]);
  readonly selectedExistingId = input<string>('');
  readonly setMode = output<'existing' | 'new'>();
  readonly selectExisting = output<string>();
  readonly createRoomType = output<void>();
}
