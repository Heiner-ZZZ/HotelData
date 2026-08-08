import { CurrencyPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { mapProduct } from '../../../products/services/products-api.service';
import type { HotelProduct } from '../../../products/models/products.model';
import { ExpensesApiService } from '../../services/expenses-api.service';

interface InvoiceLineDraft {
  productId: string;
  name: string;
  qty: number;
  unitCost: number;
  lineTotal: number;
}

@Component({
  selector: 'app-invoice-form-page',
  standalone: true,
  imports: [FormsModule, CurrencyPipe, PropertySelectorComponent],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .product-lines-section {
      margin: 18px 0 0;
      padding: 14px 16px;
      border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent);
      border-radius: 10px;
      background: color-mix(in srgb, var(--accent) 5%, transparent);
    }
    .section-heading {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 10px;
    }
    .section-heading .material-symbols-outlined {
      color: var(--accent);
      font-size: 20px;
      margin-top: 1px;
    }
    .section-heading strong { display: block; font-size: 13px; color: var(--text-primary); }
    .section-heading small { display: block; font-size: 11px; color: var(--muted-text); margin-top: 2px; }
    .line-editor {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr auto;
      gap: 8px;
      align-items: center;
    }
    .line-editor select, .line-editor input { min-width: 0; }
    .line-hint {
      font-size: 12px;
      color: var(--muted-text);
      padding: 8px 0;
    }
    .line-hint--error { color: var(--danger); }
    .line-list {
      list-style: none;
      margin: 12px 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .line-list li {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 8px;
      background: var(--surface-card);
      border: 1px solid var(--app-border);
      font-size: 13px;
    }
    .line-name { font-weight: 600; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .line-meta { color: var(--muted-text); font-variant-numeric: tabular-nums; }
    .line-total { font-weight: 700; font-variant-numeric: tabular-nums; }
    .line-remove {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border: none;
      border-radius: 6px;
      background: transparent;
      color: var(--muted-text);
      cursor: pointer;
      transition: background 120ms ease, color 120ms ease;
    }
    .line-remove:hover { background: color-mix(in srgb, var(--danger) 12%, transparent); color: var(--danger); }
    .line-remove .material-symbols-outlined { font-size: 16px; }
    .field-hint { font-size: 11px; color: var(--muted-text); margin-top: 4px; display: block; }
    @media (max-width: 720px) {
      .line-editor { grid-template-columns: 1fr 1fr; }
      .line-editor select { grid-column: 1 / -1; }
    }
  `],
  template: `
    <div class="page-wrap page-wrap--form">
      <h1 class="page-title">Nueva Factura</h1>
      <p class="page-subtitle">Registra una nueva factura de gasto operativo.</p>

      @if (error()) {
        <div class="error-banner">{{ error() }}</div>
      }

      <div class="card card--pad-24">
        @if (ctx.mode() === 'all') {
          <div style="margin-bottom: 16px;">
            <label class="field-label">Propiedad <span class="req">*</span></label>
            <app-property-selector
              [selectedPropId]="selectedPropId()"
              (propIdChange)="onPropertySelected($event)"
            />
            @if (propertyError()) {
              <div style="color: var(--danger); font-size: 11px; margin-top: 4px;">{{ propertyError() }}</div>
            }
          </div>
        }

        <div class="field-grid">
          <div class="field-grid__cell-full">
            <label class="field-label">Proveedor <span class="req">*</span></label>
            <input class="field-input" type="text" [(ngModel)]="form.vendorName" placeholder="Nombre del proveedor" />
          </div>
          <div>
            <label class="field-label">Categoría <span class="req">*</span></label>
            <input class="field-input" type="text" [(ngModel)]="form.category" placeholder="Ej: Suministros" />
          </div>
          <div>
            <label class="field-label">Monto <span class="req">*</span></label>
            <input class="field-input" type="number" [(ngModel)]="form.amount" [disabled]="productLines().length > 0" placeholder="0.00" />
            @if (productLines().length > 0) {
              <small class="field-hint">Auto-calculado desde las líneas ({{ productLines().length }})</small>
            }
          </div>
          <div>
            <label class="field-label">IVA</label>
            <input class="field-input" type="number" [(ngModel)]="form.taxAmount" placeholder="0.00" />
          </div>
          <div>
            <label class="field-label">Fecha Factura</label>
            <input class="field-input" type="date" [(ngModel)]="form.invoiceDate" />
          </div>
          <div>
            <label class="field-label">Fecha Vencimiento</label>
            <input class="field-input" type="date" [(ngModel)]="form.dueDate" />
          </div>
          <div class="field-grid__cell-full">
            <label class="field-label">Descripción</label>
            <textarea class="field-textarea" [(ngModel)]="form.description" rows="2" placeholder="Concepto de la factura..."></textarea>
          </div>
          <div class="field-grid__cell-full">
            <label class="field-label">Notas</label>
            <textarea class="field-textarea" [(ngModel)]="form.notes" rows="2" placeholder="Observaciones..."></textarea>
          </div>
        </div>

        <div class="product-lines-section">
          <div class="section-heading">
            <span class="material-symbols-outlined" aria-hidden="true">inventory_2</span>
            <div>
              <strong>Productos (restock automático)</strong>
              <small>Al guardar, cada línea aumenta el stock, actualiza el costo unitario y registra el asiento contable.</small>
            </div>
          </div>

          @if (productsLoading()) {
            <div class="line-hint">Cargando productos…</div>
          } @else if (productsError(); as err) {
            <div class="line-hint line-hint--error">
              {{ err }}
              <button class="btn btn--sm" type="button" style="margin-left: 8px;" (click)="productsResource.reload()">Reintentar</button>
            </div>
          } @else {
            <div class="line-editor">
              <select
                class="field-input"
                [ngModel]="lineForm.productId"
                (ngModelChange)="lineForm.productId = $event"
                aria-label="Producto"
              >
                <option value="">Selecciona producto…</option>
                @for (p of products(); track p.productId) {
                  <option [value]="p.productId">{{ p.name }} · stock {{ p.quantityAvailable }}</option>
                }
              </select>
              <input
                class="field-input"
                type="number"
                min="0.01"
                step="0.01"
                placeholder="Cant."
                [ngModel]="lineForm.qty"
                (ngModelChange)="lineForm.qty = $event"
                aria-label="Cantidad"
              />
              <input
                class="field-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="Costo unit."
                [ngModel]="lineForm.unitCost"
                (ngModelChange)="lineForm.unitCost = $event"
                aria-label="Costo unitario"
              />
              <button
                class="btn btn--primary"
                type="button"
                (click)="addLine()"
                [disabled]="!lineForm.productId || lineForm.qty <= 0"
              >
                <span class="material-symbols-outlined" style="font-size: 16px;">add</span>
                Agregar
              </button>
            </div>

            @if (productLines().length) {
              <ul class="line-list">
                @for (line of productLines(); track $index; let i = $index) {
                  <li>
                    <span class="line-name">{{ line.name }}</span>
                    <span class="line-meta">{{ line.qty }} × {{ line.unitCost | currency:'MXN':'symbol-narrow':'1.2-2' }}</span>
                    <span class="line-total">{{ line.lineTotal | currency:'MXN':'symbol-narrow':'1.2-2' }}</span>
                    <button type="button" class="line-remove" (click)="removeLine(i)" aria-label="Quitar línea">
                      <span class="material-symbols-outlined">close</span>
                    </button>
                  </li>
                }
              </ul>
            }
          }
        </div>

        @if (form.amount || form.taxAmount) {
          <div class="total-box">
            Total: {{ ((form.amount || 0) + (form.taxAmount || 0)) | currency:'MXN':'symbol-narrow':'1.2-2' }}
          </div>
        }

        <div style="margin-top: 20px; display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn btn--lg" type="button" (click)="cancel()">Cancelar</button>
          <button
            class="btn btn--primary btn--lg"
            type="button"
            (click)="submit()"
            [disabled]="submitting() || !form.vendorName || (productLines().length === 0 && !form.amount)"
          >
            {{ submitting() ? 'Guardando...' : 'Guardar Factura' }}
          </button>
        </div>
      </div>
    </div>
  `,
})
export class InvoiceFormPageComponent {
  private readonly api = inject(ExpensesApiService);
  private readonly router = inject(Router);
  readonly ctx = inject(PropertyContextService);
  private readonly opMode = inject(OperationModeService);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    // Página de creación → modo INSERT en el nav (ámbar).
    const releaseOperationMode = this.opMode.setMode('insert', 'Factura');
    this.destroyRef.onDestroy(releaseOperationMode);
  }

  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedPropId = signal(0);
  readonly selectedPropLabel = signal('');
  readonly propertyError = signal<string | null>(null);

  /** Draft row of the line editor (plain object, ngModel style like `form`). */
  lineForm = { productId: '', qty: 1, unitCost: 0 };

  /** Added product lines — each restocks inventory on save. */
  readonly productLines = signal<InvoiceLineDraft[]>([]);

  form = {
    vendorName: '',
    category: '',
    amount: null as number | null,
    taxAmount: null as number | null,
    invoiceDate: '',
    dueDate: '',
    description: '',
    notes: '',
  };

  /** Target property: the selector in 'all' mode, the context prop otherwise. */
  readonly invoicePropId = computed(() =>
    this.ctx.mode() === 'all' ? this.selectedPropId() : (this.ctx.currentPropId() || 0),
  );

  /** Hotel products for the line selector (httpResource recomputes on prop change). */
  readonly productsResource = httpResource<HotelProduct[]>(() => {
    const pid = this.invoicePropId();
    return pid > 0 ? `/management/products/hotels/${pid}` : undefined;
  }, {
    parse: (raw: any) => (raw?.items ?? []).map(mapProduct),
  });

  readonly products = computed(() => this.productsResource.value() ?? []);
  readonly productsLoading = computed(() => this.productsResource.isLoading());
  readonly productsError = computed<string | null>(() =>
    this.productsResource.error() ? 'No se pudieron cargar los productos.' : null,
  );

  readonly linesTotal = computed(() =>
    Math.round(this.productLines().reduce((acc, l) => acc + l.lineTotal, 0) * 100) / 100,
  );

  addLine(): void {
    const productId = this.lineForm.productId;
    const qty = Number(this.lineForm.qty) || 0;
    const unitCost = Number(this.lineForm.unitCost) || 0;
    if (!productId || qty <= 0) return;

    const product = this.products().find((p) => p.productId === productId);
    const lineTotal = Math.round(qty * unitCost * 100) / 100;
    this.productLines.update((lines) => [
      ...lines,
      { productId, name: product?.name ?? productId, qty, unitCost, lineTotal },
    ]);
    // Amount is auto-calculated from the lines while any exist.
    this.form.amount = this.linesTotal();
    this.lineForm = { productId: '', qty: 1, unitCost: 0 };
  }

  removeLine(index: number): void {
    this.productLines.update((lines) => lines.filter((_, i) => i !== index));
    this.form.amount = this.productLines().length ? this.linesTotal() : null;
  }

  submit() {
    const lines = this.productLines();
    const amount = lines.length ? this.linesTotal() : (this.form.amount ?? 0);
    if (!this.form.vendorName || amount <= 0) return;

    if (this.ctx.mode() === 'all' && this.selectedPropId() <= 0) {
      this.propertyError.set('Selecciona una propiedad para continuar.');
      return;
    }
    this.propertyError.set(null);

    this.submitting.set(true);
    this.error.set(null);

    this.api.createInvoice({
      vendor_name: this.form.vendorName,
      category: this.form.category,
      amount,
      tax_amount: this.form.taxAmount || 0,
      invoice_date: this.form.invoiceDate,
      due_date: this.form.dueDate,
      description: this.form.description,
      notes: this.form.notes,
      prop_id: this.ctx.mode() === 'all' ? this.selectedPropId() : (this.ctx.currentPropId() || undefined),
      ...(lines.length
        ? { product_lines: lines.map((l) => ({ product_id: l.productId, qty: l.qty, unit_cost: l.unitCost })) }
        : {}),
    }).subscribe({
      next: () => {
        this.router.navigate(['/management/expenses/invoices']);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al crear factura');
        this.submitting.set(false);
      },
    });
  }

  onPropertySelected(event: { propId: number; label: string }) {
    this.selectedPropId.set(event.propId);
    this.selectedPropLabel.set(event.label);
    this.propertyError.set(null);
    // Lines belong to a hotel — drop them when the target changes.
    this.productLines.set([]);
    this.lineForm = { productId: '', qty: 1, unitCost: 0 };
  }

  cancel() { this.router.navigate(['/management/expenses/invoices']); }
}
