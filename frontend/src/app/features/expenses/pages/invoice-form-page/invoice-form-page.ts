import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ExpensesApiService } from '../../services/expenses-api.service';

@Component({
  selector: 'app-invoice-form-page',
  standalone: true,
  imports: [FormsModule, CurrencyPipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="max-width: 650px; margin: 0 auto; padding: 24px;">
      <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0 0 4px;">Nueva Factura</h1>
      <p style="font-size: 13px; color: #64748b; margin: 0 0 24px;">Registra una nueva factura de gasto operativo.</p>

      @if (error()) {
        <div style="padding: 10px 14px; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; font-size: 12px; margin-bottom: 16px;">{{ error() }}</div>
      }

      <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          <div style="grid-column: 1 / -1;">
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Proveedor <span style="color: #dc2626;">*</span></label>
            <input type="text" [(ngModel)]="form.vendorName" placeholder="Nombre del proveedor"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div>
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Categoría <span style="color: #dc2626;">*</span></label>
            <input type="text" [(ngModel)]="form.category" placeholder="Ej: Suministros"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div>
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Monto <span style="color: #dc2626;">*</span></label>
            <input type="number" [(ngModel)]="form.amount" placeholder="0.00"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div>
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">IVA</label>
            <input type="number" [(ngModel)]="form.taxAmount" placeholder="0.00"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div>
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Fecha Factura</label>
            <input type="date" [(ngModel)]="form.invoiceDate"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div>
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Fecha Vencimiento</label>
            <input type="date" [(ngModel)]="form.dueDate"
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
          </div>
          <div style="grid-column: 1 / -1;">
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Descripción</label>
            <textarea [(ngModel)]="form.description" rows="2" placeholder="Concepto de la factura..."
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; box-sizing: border-box; resize: vertical; outline: none;"></textarea>
          </div>
          <div style="grid-column: 1 / -1;">
            <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Notas</label>
            <textarea [(ngModel)]="form.notes" rows="2" placeholder="Observaciones..."
              style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; box-sizing: border-box; resize: vertical; outline: none;"></textarea>
          </div>
        </div>

        @if (form.amount || form.taxAmount) {
          <div style="margin-top: 16px; padding: 12px; background: #f0f4ff; border-radius: 8px; font-size: 14px; font-weight: 600; color: #1e40af; text-align: right;">
            Total: {{ ((form.amount || 0) + (form.taxAmount || 0)) | currency:'MXN':'symbol-narrow':'1.2-2' }}
          </div>
        }

        <div style="margin-top: 20px; display: flex; gap: 12px; justify-content: flex-end;">
          <button (click)="cancel()"
            style="padding: 10px 20px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; cursor: pointer;">Cancelar</button>
          <button (click)="submit()" [disabled]="submitting() || !form.vendorName || !form.amount"
            style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; &:disabled { opacity: 0.4; }">
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

  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);

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

  cancel() { this.router.navigate(['/management/expenses/invoices']); }
}
