import { CurrencyPipe, KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-charges',
  standalone: true,
  imports: [CurrencyPipe, KeyValuePipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 2</div>
      <h2 class="co-step-title">Agregar cargos adicionales</h2>

      <!-- Quick charge buttons -->
      <div class="co-quick-charges">
        <span class="co-label">Cargos r&aacute;pidos</span>
        <div class="co-quick-grid">
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'minibar', concept: 'Minibar', amount: 15 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">liquor</span> Minibar \$15
          </button>
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'spa', concept: 'Spa', amount: 40 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">spa</span> Spa \$40
          </button>
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'parking', concept: 'Parking', amount: 10 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">local_parking</span> Parking \$10
          </button>
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'mascotas', concept: 'Mascotas', amount: 25 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">pets</span> Mascotas \$25
          </button>
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'lavanderia', concept: 'Lavander&iacute;a', amount: 20 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">local_laundry_service</span> Lavander&iacute;a \$20
          </button>
          <button class="co-quick-btn" (click)="quickCharge.emit({ cat: 'late_checkout', concept: 'Late Checkout', amount: 30 })" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">schedule</span> Late Checkout \$30
          </button>
        </div>
      </div>

      <!-- Custom charge -->
      <div class="co-custom-charge">
        <button class="co-toggle-charge-form" (click)="toggleForm.emit()">
          <span class="material-symbols-outlined">{{ chargeFormVisible() ? 'expand_less' : 'add_circle' }}</span>
          {{ chargeFormVisible() ? 'Cancelar' : 'Otro cargo personalizado' }}
        </button>

        @if (chargeFormVisible()) {
          <div class="co-charge-form">
            @if (chargeError()) { <div class="co-form-error"><span class="material-symbols-outlined">error</span> {{ chargeError() }}</div> }
            <div class="co-charge-grid">
              <div class="co-cf-field co-cf-wide">
                <span class="co-label">Concepto</span>
                <input type="text" class="co-input" placeholder="Ej. Toallas extra, Da&ntilde;o"
                  [ngModel]="chargeConcept()" (ngModelChange)="chargeConceptChange.emit($event)" />
              </div>
              <div class="co-cf-field">
                <span class="co-label">Categor&iacute;a</span>
                <select class="co-select" [ngModel]="chargeCategory()" (ngModelChange)="chargeCategoryChange.emit($event)">
                  @for (cat of chargeCategories(); track cat.value) {
                    <option [value]="cat.value">{{ cat.label }}</option>
                  }
                </select>
              </div>
              <div class="co-cf-field">
                <span class="co-label">Monto</span>
                <input type="number" step="0.01" min="0" class="co-input" placeholder="0.00"
                  [ngModel]="chargeAmount()" (ngModelChange)="chargeAmountChange.emit(Number($event))" />
              </div>
              <div class="co-cf-field">
                <span class="co-label">Cantidad</span>
                <input type="number" min="1" class="co-input"
                  [ngModel]="chargeQuantity()" (ngModelChange)="chargeQuantityChange.emit(Math.max(1, Number($event)))" />
              </div>
              <div class="co-cf-field co-cf-wide">
                <span class="co-label">Nota</span>
                <input type="text" class="co-input" placeholder="Detalle"
                  [ngModel]="chargeNote()" (ngModelChange)="chargeNoteChange.emit($event)" />
              </div>
            </div>
            <button class="co-btn-charge-add" (click)="addCharge.emit()" [disabled]="chargeSaving()">
              <span class="material-symbols-outlined">add</span> Agregar cargo
            </button>
          </div>
        }
      </div>

      <!-- Current charges summary -->
      @if (chargesByCategory().length > 0) {
        <div class="co-current-charges">
          <span class="co-label">Cargos actuales ({{ chargesTotal() | currency:currency() }})</span>
          <div class="co-charge-chips">
            @for (catEntry of chargesByCategory(); track catEntry.key) {
              @if (catEntry.items.length) {
                <span class="co-cat-chip">
                  <span class="material-symbols-outlined co-cat-chip-icon">{{ catEntry.icon }}</span>
                  {{ catEntry.label }}: {{ catEntry.total | currency:currency() }}
                </span>
              }
            }
          </div>
        </div>
      }

      <div class="co-step-actions">
        <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
        <button class="co-btn-primary" (click)="next.emit()">Continuar &rarr;</button>
      </div>
    </section>
  `
})
export class CoStepChargesComponent {
  readonly chargeFormVisible = input(false);
  readonly chargeError = input('');
  readonly chargeConcept = input('');
  readonly chargeCategory = input('');
  readonly chargeAmount = input(0);
  readonly chargeQuantity = input(1);
  readonly chargeNote = input('');
  readonly chargeSaving = input(false);
  readonly chargesTotal = input(0);
  readonly chargesByCategory = input<any[]>([]);
  readonly chargeCategories = input<any[]>([]);
  readonly currency = input('USD');

  readonly Math = Math;
  readonly Number = Number;

  readonly toggleForm = output<void>();
  readonly chargeConceptChange = output<string>();
  readonly chargeCategoryChange = output<string>();
  readonly chargeAmountChange = output<number>();
  readonly chargeQuantityChange = output<number>();
  readonly chargeNoteChange = output<string>();
  readonly addCharge = output<void>();
  readonly quickCharge = output<{ cat: string; concept: string; amount: number }>();
  readonly prev = output<void>();
  readonly next = output<void>();
}
