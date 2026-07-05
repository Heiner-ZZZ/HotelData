import { ReactiveFormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, ElementRef, input, output, viewChild } from '@angular/core';

@Component({
  selector: 'app-rp-edit-modal',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="modal-overlay" (click)="cancel.emit()">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-head">
          <span class="material-symbols-outlined modal-head-icon">edit</span>
          <div>
            <h2>Editar: {{ roomTypeName() }}</h2>
            <p>{{ roomTypeId() }}</p>
          </div>
          <button type="button" class="modal-close" (click)="cancel.emit()" aria-label="Cerrar">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        <form [formGroup]="editForm()" (submit)="$event.preventDefault(); save.emit()" class="form-grid">
          <label class="field">
            <span class="field-label">Nombre</span>
            <input formControlName="name" placeholder="Ej: Suite Premium">
          </label>
          <label class="field">
            <span class="field-label">Descripción</span>
            <textarea rows="3" formControlName="description" placeholder="Opcional"></textarea>
          </label>
          <label class="field">
            <span class="field-label">N° Habitación</span>
            <input formControlName="roomNumber" placeholder="Ej: 101">
          </label>
          <label class="field">
            <span class="field-label">Piso / PB</span>
            <input formControlName="floor" placeholder="Ej: 1, 2, PB">
          </label>
          <label class="field">
            <span class="field-label">Adultos máx.</span>
            <input type="number" min="1" formControlName="maxAdults">
          </label>
          <label class="field">
            <span class="field-label">Niños máx.</span>
            <input type="number" min="0" formControlName="maxChildren">
          </label>
          <label class="field">
            <span class="field-label">Capacidad base</span>
            <input type="number" min="1" formControlName="baseCapacity">
          </label>
          <label class="field">
            <span class="field-label">Tarifa base ($/noche)</span>
            <input type="number" min="0" step="0.01" formControlName="baseRate" placeholder="0 = sin tarifa base">
          </label>
          <label class="field">
            <span class="field-label">Vista</span>
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
            <span class="field-label">Imagen</span>
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
                  @if (selectedFile()) {
                    <button type="button" class="image-preview-upload-btn" (click)="uploadSelectedFile()" [disabled]="uploading()">
                      @if (uploading()) {
                        <span class="material-symbols-outlined spin">progress_activity</span>
                      } @else {
                        <span class="material-symbols-outlined">cloud_upload</span>
                      }
                      {{ uploading() ? 'Subiendo...' : 'Subir' }}
                    </button>
                  }
                </div>
              </div>
            }
          </label>
          <label class="field checkbox-field">
            <span class="field-label"><span class="material-symbols-outlined">smoking_rooms</span> Fumador</span>
            <input type="checkbox" formControlName="smoking">
          </label>
          <label class="field checkbox-field">
            <span class="field-label"><span class="material-symbols-outlined">accessible</span> Accesible</span>
            <input type="checkbox" formControlName="accessible">
          </label>
          <label class="field checkbox-field">
            <span class="field-label">Activo</span>
            <input type="checkbox" formControlName="isActive">
          </label>

          <!-- Features section -->
          <div class="features-section" style="grid-column: 1 / -1">
            <div class="features-section-head" (click)="togglePanel.emit()">
              <span class="material-symbols-outlined features-head-icon">stars</span>
              <span class="features-head-title">Características</span>
              <span class="features-count-badge" [class.has-selection]="selectedCount() > 0">
                {{ selectedCount() }} seleccionadas
              </span>
              <span class="material-symbols-outlined features-chevron" [class.open]="panelOpen()">
                {{ panelOpen() ? 'expand_less' : 'expand_more' }}
              </span>
            </div>
            @if (panelOpen()) {
              @if (catalog().length > 0) {
                <div class="features-search-wrap">
                  <span class="material-symbols-outlined features-search-icon">search</span>
                  <input class="features-search-input" type="text" placeholder="Buscar características…"
                    [value]="searchQuery()" (input)="searchChange.emit($any($event.target).value)"
                    (click)="$event.stopPropagation()" />
                  @if (searchQuery()) {
                    <button type="button" class="features-search-clear" (click)="searchChange.emit(''); $event.stopPropagation()">
                      <span class="material-symbols-outlined">close</span>
                    </button>
                  }
                </div>
                <div class="features-catalog">
                  @for (cat of filteredCatalog(); track cat.category) {
                    <div class="feature-category">
                      <span class="feature-category-label">{{ cat.category }}</span>
                      <div class="feature-items">
                        @for (feat of cat.items; track feat.label) {
                          <button type="button" class="feature-chip" [class.is-selected]="isFeatureSelected(feat.label)"
                            (click)="toggleFeature.emit(feat.label)" title="{{ feat.label }}">
                            @if (feat.icon) { <span class="material-symbols-outlined feature-chip-icon">{{ feat.icon }}</span> }
                            <span class="feature-chip-label">{{ feat.label }}</span>
                            @if (feat.source === 'amenity') { <span class="feature-source-badge" title="Del catálogo de amenidades">A</span> }
                            @else if (feat.custom) { <span class="feature-source-badge feature-source-badge--custom" title="Personalizada">+</span> }
                          </button>
                        }
                      </div>
                    </div>
                  }
                </div>
              } @else {
                <p class="features-loading">Cargando catálogo de características...</p>
              }
            }
          </div>

          <div class="modal-actions" style="grid-column: 1 / -1">
            <button type="button" class="btn-secondary" (click)="cancel.emit()">Cancelar</button>
            <button type="submit" class="btn-primary" [disabled]="saving()">
              @if (saving()) {
                <span class="material-symbols-outlined spin">progress_activity</span>
              } @else {
                <span class="material-symbols-outlined">save</span>
              }
              Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>
  `
})
export class RpEditModalComponent {
  readonly editForm = input<any>(null);
  readonly roomTypeName = input('');
  readonly roomTypeId = input('');
  readonly saving = input(false);
  readonly panelOpen = input(false);
  readonly catalog = input<any[]>([]);
  readonly filteredCatalog = input<any[]>([]);
  readonly searchQuery = input('');
  readonly selectedCount = input(0);
  readonly isSelected = input<(label: string) => boolean>(() => false);
  readonly imagePreviewUrl = input('');
  readonly uploading = input(false);
  readonly selectedFile = input<File | null>(null);

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

  uploadSelectedFile() {
    // Parent handles the actual upload
    this.uploadFile.emit();
  }

  readonly uploadFile = output<void>();

  /** Wrapper method — InputSignal cannot be called with args in templates */
  isFeatureSelected(label: string): boolean {
    return this.isSelected()(label);
  }

  readonly cancel = output<void>();
  readonly save = output<void>();
  readonly togglePanel = output<void>();
  readonly searchChange = output<string>();
  readonly toggleFeature = output<string>();
}
