import { ReactiveFormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, ElementRef, input, output, viewChild } from '@angular/core';
import { AiSuggestDirective } from '../../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-rp-create-form',
  standalone: true,
  imports: [ReactiveFormsModule, AiSuggestDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card form-panel create-form-panel">
      <div class="panel-head">
        <span class="material-symbols-outlined panel-head-icon create-entry-icon">add_business</span>
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
            <span class="material-symbols-outlined field-icon">tag</span>
            N° Habitación
          </span>
          <input formControlName="roomNumber" placeholder="Ej: 101">
        </label>
        <label class="field" style="grid-column: 1 / -1">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">description</span>
            Descripción
          </span>
          <textarea rows="3" formControlName="description" placeholder="Opcional" appAiSuggest="descripcion_habitacion"></textarea>
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
        <label class="field" style="grid-column: 1 / -1">
          <span class="field-label">
            <span class="material-symbols-outlined field-icon">image</span>
            Imagen
          </span>
          <div class="room-image-input-group">
            <div class="image-url-input-wrap">
              <span class="material-symbols-outlined input-icon">image</span>
              <input formControlName="imageUrl" type="url" placeholder="https://ejemplo.com/habitacion.jpg" (input)="onImageUrlChange($any($event.target).value)" />
            </div>
            <div class="image-upload-divider">
              <span>o</span>
            </div>
            <input #fileInput type="file" accept="image/*" (change)="onFileSelected($event)" style="display: none" />
            <button type="button" class="btn-outline" (click)="triggerFileInput()">
              <span class="material-symbols-outlined">folder_open</span>
              Subir archivo
            </button>
          </div>
          @if (imagePreviewUrl()) {
            <div class="image-preview-thumb" [class.uploading]="uploading()">
              <img [src]="imagePreviewUrl()" alt="Preview" />
              <div class="image-preview-actions">
                <button type="button" class="image-preview-clear" (click)="clearImageUrl()" aria-label="Quitar imagen">
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            </div>
          }
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
          <button type="button" class="btn-outline" (click)="cancel.emit()">
            <span class="material-symbols-outlined btn-icon">close</span>
            Cancelar
          </button>
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
  readonly imagePreviewUrl = input('');
  readonly uploading = input(false);
  readonly selectedFile = input<File | null>(null);

  readonly setMode = output<'existing' | 'new'>();
  readonly selectExisting = output<string>();
  readonly createRoomType = output<void>();
  readonly cancel = output<void>();
  readonly imageUrlChange = output<string>();
  readonly fileSelected = output<File>();

  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  onImageUrlChange(value: string) {
    this.imageUrlChange.emit(value);
  }

  clearImageUrl() {
    this.imageUrlChange.emit('');
  }

  triggerFileInput() {
    this.fileInput()?.nativeElement.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return;
    this.fileSelected.emit(file);
  }
}
