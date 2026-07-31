import { ChangeDetectionStrategy, Component, DestroyRef, inject, input, OnInit, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsApiService } from '../../services/products-api.service';
import type { HotelProduct, RestockResult } from '../../models/products.model';

@Component({
  selector: 'app-products-restock-modal',
  imports: [ReactiveFormsModule],
  templateUrl: './products-restock-modal.html',
  styleUrl: './products-restock-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductsRestockModalComponent implements OnInit {
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsApi = inject(ProductsApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  /** Product being restocked. Required input — modal renders nothing meaningful without it. */
  readonly product = input.required<HotelProduct>();
  /** Emits when the modal is closed (cancel button, backdrop click, or success path cleanup). */
  readonly close = output<void>();
  /** Emits when restock succeeds; parent refreshes product list / closes modal as needed. */
  readonly success = output<RestockResult>();

  readonly form: FormGroup = this.fb.nonNullable.group({
    qty: [1, [Validators.required, Validators.min(0.01)]],
    unit_cost: [0, [Validators.required, Validators.min(0)]],
    supplier_name: ['', []],
    invoice_ref: ['', []],
  });

  readonly saving = signal(false);
  readonly submitError = signal<string | null>(null);

  /** Live preview of the total restock cost. */
  readonly totalPreview = signal(0);

  /**
   * Required inputs are only bound AFTER the constructor runs, so we cannot
   * read ``this.product()`` in the constructor body. ngOnInit guarantees the
   * input has a value when we pre-fill the form.
   */
  ngOnInit(): void {
    const p = this.product();
    this.form.patchValue({
      unit_cost: p.costPrice ?? 0,
      supplier_name: p.defaultSupplier ?? '',
    });
    this.recalcTotal();

    this.form.controls['qty'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.recalcTotal());
    this.form.controls['unit_cost'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.recalcTotal());
  }

  fieldError(fieldName: string): string | null {
    const ctrl = this.form.get(fieldName);
    if (!ctrl || !ctrl.touched || ctrl.valid) return null;
    if (ctrl.hasError('required')) return 'Requerido';
    if (ctrl.hasError('min')) {
      const min = ctrl.getError('min').min;
      return `Debe ser ≥ ${min}`;
    }
    return 'Valor inválido';
  }

  private recalcTotal(): void {
    const qty = Number(this.form.controls['qty'].value ?? 0);
    const cost = Number(this.form.controls['unit_cost'].value ?? 0);
    this.totalPreview.set(Math.round(qty * cost * 100) / 100);
  }

  submit(): void {
    if (this.form.invalid || this.saving()) {
      this.form.markAllAsTouched();
      return;
    }
    const propId = this.propCtx.currentPropId();
    if (!propId) {
      this.submitError.set('No hay propiedad seleccionada.');
      return;
    }

    const v = this.form.getRawValue();
    this.saving.set(true);
    this.submitError.set(null);

    this.productsApi
      .restockProduct(propId, this.product().productId, {
        qty: Number(v.qty),
        unit_cost: Number(v.unit_cost),
        supplier_name: v.supplier_name || undefined,
        invoice_ref: v.invoice_ref || undefined,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.saving.set(false);
          this.success.emit(result);
        },
        error: (err: any) => {
          this.saving.set(false);
          const msg = err?.error?.detail ?? err?.message ?? 'Error al registrar restock.';
          this.submitError.set(msg);
        },
      });
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget && !this.saving()) {
      this.close.emit();
    }
  }

  cancel(): void {
    if (!this.saving()) this.close.emit();
  }
}