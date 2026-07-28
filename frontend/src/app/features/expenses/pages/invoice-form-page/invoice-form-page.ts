import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ExpensesApiService } from '../../services/expenses-api.service';@Component({
  selector: 'app-invoice-form-page',
  standalone: true,
  imports: [FormsModule, CurrencyPipe, PropertySelectorComponent],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
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
            <input class="field-input" type="number" [(ngModel)]="form.amount" placeholder="0.00" />
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

        @if (form.amount || form.taxAmount) {
          <div class="total-box">
            Total: {{ ((form.amount || 0) + (form.taxAmount || 0)) | currency:'MXN':'symbol-narrow':'1.2-2' }}
          </div>
        }

        <div style="margin-top: 20px; display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn btn--lg" type="button" (click)="cancel()">Cancelar</button>
          <button class="btn btn--primary btn--lg" type="button" (click)="submit()" [disabled]="submitting() || !form.vendorName || !form.amount">
            {{ submitting() ? 'Guardando...' : 'Guardar Factura' }}
          </button>
        </div>
      </div>
    </div>
  `
})
export class InvoiceFormPageComponent {
  private readonly api = inject(ExpensesApiService);
  private readonly router = inject(Router);
  readonly ctx = inject(PropertyContextService);

  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly selectedPropId = signal(0);
  readonly selectedPropLabel = signal('');
  readonly propertyError = signal<string | null>(null);

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

  submit() {
    if (!this.form.vendorName || !this.form.amount) return;

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
      amount: this.form.amount,
      tax_amount: this.form.taxAmount || 0,
      invoice_date: this.form.invoiceDate,
      due_date: this.form.dueDate,
      description: this.form.description,
      notes: this.form.notes,
      prop_id: this.ctx.mode() === 'all' ? this.selectedPropId() : (this.ctx.currentPropId() || undefined),
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
  }

  cancel() { this.router.navigate(['/management/expenses/invoices']); }
}
