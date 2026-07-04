import { CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';

import { ConfirmDialogService } from '../../../../../shared/ui/confirm-dialog/confirm-dialog.service';

@Component({
  selector: 'app-co-step-charges',
  standalone: true,
  imports: [CurrencyPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 2</div>
      <h2 class="co-step-title">Agregar cargos adicionales</h2>

      <!-- Quick charge buttons -->
      <div class="co-quick-charges">
        <span class="co-label">Cargos r&aacute;pidos</span>
        <div class="co-quick-grid">
          <button class="co-quick-btn" (click)="openQuickEditor('minibar', 'Minibar', 15)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">liquor</span> Minibar $15
          </button>
          <button class="co-quick-btn" (click)="openQuickEditor('spa', 'Spa', 40)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">spa</span> Spa $40
          </button>
          <button class="co-quick-btn" (click)="openQuickEditor('parking', 'Parking', 10)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">local_parking</span> Parking $10
          </button>
          <button class="co-quick-btn" (click)="openQuickEditor('mascotas', 'Mascotas', 25)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">pets</span> Mascotas $25
          </button>
          <button class="co-quick-btn" (click)="openQuickEditor('lavanderia', 'Lavander&iacute;a', 20)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">local_laundry_service</span> Lavander&iacute;a $20
          </button>
          <button class="co-quick-btn" (click)="openQuickEditor('late_checkout', 'Late Checkout', 30)" [disabled]="chargeSaving()">
            <span class="material-symbols-outlined">schedule</span> Late Checkout $30
          </button>
        </div>

        @if (quickEditor(); as editor) {
          <div class="co-quick-editor">
            <span class="co-qe-title">{{ editor.concept }}</span>
            <div class="co-qe-row">
              <label class="co-qe-label">
                Cantidad
                <input type="number" class="co-qe-input" min="1" max="99"
                       [ngModel]="editor.quantity"
                       (ngModelChange)="quickEditor.update(e => e ? {...e, quantity: Math.max(1, Number($event))} : null)" />
              </label>
              <span class="co-qe-total">
                Total: <strong>{{ (editor.amount * editor.quantity) | currency:currency() }}</strong>
              </span>
            </div>
            <div class="co-qe-actions">
              <button class="co-qe-cancel" (click)="quickEditor.set(null)">Cancelar</button>
              <button class="co-qe-confirm" (click)="confirmQuickCharge(editor)" [disabled]="chargeSaving()">
                Agregar
              </button>
            </div>
          </div>
        }
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

      <!-- Current charges summary with delete buttons -->
      @if (chargesByCategory().length > 0) {
        <div class="co-current-charges">
          <span class="co-label">Cargos actuales ({{ chargesTotal() | currency:currency() }})</span>
          <div class="co-charge-chips">
            @for (catEntry of chargesByCategory(); track catEntry.key) {
              @for (item of catEntry.items; track item.id || item.concept + item.created_at) {
                <span class="co-cat-chip co-cat-chip-removable">
                  <span class="material-symbols-outlined co-cat-chip-icon">{{ catEntry.icon }}</span>
                  {{ item.concept }}: {{ item.total | currency:currency() }}
                  <button class="co-chip-delete"
                          [disabled]="chargeSaving()"
                          (click)="confirmDelete(item.id || '', item.concept)"
                          title="Eliminar cargo">
                    <span class="material-symbols-outlined">close</span>
                  </button>
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

  readonly confirmDialog = inject(ConfirmDialogService);

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
  readonly deleteCharge = output<string>();
  readonly prev = output<void>();
  readonly next = output<void>();

  readonly quickEditor = signal<{ cat: string; concept: string; amount: number; quantity: number } | null>(null);

  openQuickEditor(cat: string, concept: string, baseAmount: number): void {
    this.quickEditor.set({ cat, concept, amount: baseAmount, quantity: 1 });
  }

  confirmQuickCharge(editor: { cat: string; concept: string; amount: number; quantity: number }): void {
    const total = editor.amount * editor.quantity;
    this.quickCharge.emit({ cat: editor.cat, concept: editor.concept, amount: total });
    this.quickEditor.set(null);
  }

  async confirmDelete(chargeId: string, concept: string): Promise<void> {
    if (!chargeId) return;
    const ok = await this.confirmDialog.open({
      title: 'Eliminar cargo',
      message: `¿Eliminar el cargo "${concept}"?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
    });
    if (ok) this.deleteCharge.emit(chargeId);
  }
}
