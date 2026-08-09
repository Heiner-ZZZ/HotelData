import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, input, OnInit, output, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import type { InvoiceDetail, InvoiceListItem, InvoiceProductLine } from '../../../expenses/models/expenses.model';
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
  private readonly expensesApi = inject(ExpensesApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

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
    invoice_id: ['', []],
  });

  readonly saving = signal(false);
  readonly submitError = signal<string | null>(null);

  /** Expense invoices of the current hotel, for the real-link selector. */
  readonly invoices = signal<InvoiceListItem[]>([]);
  readonly invoicesLoading = signal(false);
  readonly invoicesError = signal<string | null>(null);

  /** True when the linked invoice was deleted between list-load and submit. */
  readonly invoiceMissing = signal(false);

  /** True when the linked invoice was rejected after list-load (rare race). */
  readonly invoiceRejected = signal(false);

  /**
   * Full detail of the invoice currently selected in the selector. Fetched
   * lazily on selection so the inverse link can tell whether THIS product was
   * already restocked by that invoice (with qty + date). Null until a
   * non-empty invoice is chosen (or the fetch failed).
   */
  readonly invoiceDetail = signal<InvoiceDetail | null>(null);
  readonly invoiceDetailLoading = signal(false);

  /**
   * Product line of THIS product inside the selected invoice, when it was
   * already restocked there. Drives the "ya fue repuesto por esta factura"
   * inverse link. Null when the invoice never touched this product.
   */
  readonly alreadyRestockedLine = computed<InvoiceProductLine | null>(() => {
    const detail = this.invoiceDetail();
    if (!detail) return null;
    const pid = this.product().productId;
    return detail.productLines.find((l) => l.productId === pid && l.restocked) ?? null;
  });

  /**
   * True once the user deliberately cleared the invoice select (picked
   * 'Sin factura'). From then on the auto-suggestion must NOT re-select an
   * invoice — the empty selection is an intentional no-link choice.
   *
   * Only user-driven clears count: the form STARTS empty (that's the default,
   * not a choice), so the invoice_id subscription is inert until invoices
   * have loaded (``invoicesLoaded``) and the auto-selection settled.
   */
  private userClearedInvoice = false;
  private invoicesLoaded = false;

  /** Live preview of the total restock cost. */
  readonly totalPreview = signal(0);

  /**
   * Reactive mirror of the supplier control (form controls are NOT signals,
   * so the computed below needs a signal source to re-evaluate when the user
   * edits the supplier). Initial value '' matches the untouched form.
   */
  private readonly supplierName = toSignal(
    this.form.controls['supplier_name'].valueChanges,
    { initialValue: '' },
  );

  /**
   * Most recent expense invoice whose vendor matches the product's supplier
   * (case/whitespace-insensitive). Auto-selected on load to avoid duplicate
   * registration: the supplier field defaults to the product's
   * ``defaultSupplier``, so a matching purchase invoice is the likely target.
   * Null when the supplier matches nothing.
   */
  readonly suggestedInvoice = computed<InvoiceListItem | null>(() => {
    const supplier = (this.supplierName() ?? '').trim().toLowerCase();
    if (!supplier) return null;
    const match = this.invoices()
      .filter((inv) => String(inv.vendorName ?? '').trim().toLowerCase() === supplier)
      .sort((a, b) => (b.createdAt ?? '').localeCompare(a.createdAt ?? ''))[0];
    return match ?? null;
  });

  /** Short hint explaining the auto-selected invoice (or why none was picked). */
  readonly suggestionHint = computed<string | null>(() => {
    const inv = this.suggestedInvoice();
    if (!inv) return null;
    const chosen = this.form.get('invoice_id')?.value as string;
    return chosen === inv.id
      ? `Vinculada a la factura más reciente de ${inv.vendorName}.`
      : `Factura sugerida de ${inv.vendorName} — se vinculará al guardar.`;
  });

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
    this.loadInvoices();

    this.form.controls['qty'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.recalcTotal());
    this.form.controls['unit_cost'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.recalcTotal());
    // Keep the suggestion live: if the user types/edits the supplier to match
    // an existing invoice (and hasn't picked one manually), select it — the
    // !current guard makes this a no-op once they chose anything, including
    // an intentional 'Sin factura (restock manual)'.
    // When the user clears the select (either picking 'Sin factura' or the
    // stale-invoice flow), stop auto-selecting: an empty invoice_id is now an
    // intentional no-link choice, not a gap to fill. Inert until invoices
    // load so the form's initial empty value isn't mistaken for a clear.
    this.form.controls['invoice_id'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value) => {
        if (this.invoicesLoaded && !String(value ?? '').trim()) {
          this.userClearedInvoice = true;
        }
        this.loadSelectedInvoiceDetail(String(value ?? '').trim());
      });
    this.form.controls['supplier_name'].valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.preselectSuggestedInvoice());
  }

  /** Load the current hotel's expense invoices for the link selector. */
  loadInvoices(): void {
    const propId = this.propCtx.currentPropId();
    if (!propId) {
      this.invoicesError.set('No hay propiedad seleccionada.');
      return;
    }
    this.invoicesLoading.set(true);
    this.invoicesError.set(null);
    this.expensesApi
      .getInvoices('pending,approved,paid', undefined, undefined, 1, propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.invoices.set(res.items);
          this.invoicesLoading.set(false);
          this.invoicesLoaded = true;
          this.preselectSuggestedInvoice();
        },
        error: () => {
          this.invoicesLoading.set(false);
          this.invoicesError.set('No se pudieron cargar las facturas.');
        },
      });
  }

  /**
   * Auto-select the supplier's most recent invoice, but NEVER override a
   * choice the user already made: only fires while ``invoice_id`` is empty
   * (the select is untouched — either never picked or an intentional
   * 'Sin factura' reset, which must NOT be fought).
   */
  private preselectSuggestedInvoice(): void {
    const suggested = this.suggestedInvoice();
    const current = String(this.form.get('invoice_id')?.value ?? '').trim();
    if (suggested && !current && !this.userClearedInvoice) {
      this.form.patchValue({ invoice_id: suggested.id });
    }
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

  /**
   * Fetch the selected invoice's detail to power the inverse link. Clears the
   * current detail immediately so switching invoices never shows a stale
   * "ya repuesto" notice. A response that lands after the user switched to
   * another invoice is discarded (stale-guard by id comparison).
   */
  private loadSelectedInvoiceDetail(invoiceId: string): void {
    this.invoiceDetail.set(null);
    if (!invoiceId) {
      this.invoiceDetailLoading.set(false);
      return;
    }
    this.invoiceDetailLoading.set(true);
    this.expensesApi
      .getInvoice(invoiceId, this.propCtx.currentPropId())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          if (String(this.form.get('invoice_id')?.value ?? '').trim() !== invoiceId) return;
          this.invoiceDetail.set(detail);
          this.invoiceDetailLoading.set(false);
        },
        error: () => {
          if (String(this.form.get('invoice_id')?.value ?? '').trim() !== invoiceId) return;
          this.invoiceDetail.set(null);
          this.invoiceDetailLoading.set(false);
        },
      });
  }

  /** Real href so the inverse link degrades gracefully (open in new tab). */
  invoiceDetailHref(): string {
    const detail = this.invoiceDetail();
    if (!detail) return '';
    const pid = this.propCtx.currentPropId();
    return `/management/expenses/invoices/${detail.id}${pid ? `?prop_id=${pid}` : ''}`;
  }

  /**
   * Inverse link: jump from the restock modal to the invoice detail page,
   * where the 'Restocks vinculados' reverse view lists this very line.
   */
  openInvoiceDetail(event: Event): void {
    event.preventDefault();
    const detail = this.invoiceDetail();
    if (!detail) return;
    void this.router.navigate(['/management/expenses/invoices', detail.id], {
      queryParams: this.propCtx.currentPropId() ? { prop_id: this.propCtx.currentPropId() } : {},
    });
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
    const invoiceId = v.invoice_id?.trim() ?? '';
    this.invoiceMissing.set(false);
    this.invoiceRejected.set(false);
    this.saving.set(true);
    this.submitError.set(null);

    this.productsApi
      .restockProduct(propId, this.product().productId, {
        qty: Number(v.qty),
        unit_cost: Number(v.unit_cost),
        supplier_name: v.supplier_name || undefined,
        invoice_id: invoiceId || undefined,
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
          // Only a 400 that explicitly mentions the invoice means the linked
          // invoice is gone. Validation 400s (qty/unit_cost) must NOT drop the
          // user's selection.
          const isInvoiceError =
            err?.status === 400 && invoiceId && /factura/i.test(String(msg));
          if (isInvoiceError) {
            const rejected = /rechazada|rechazado/i.test(String(msg));
            this.invoiceRejected.set(rejected);
            // A rejected invoice exists but can't back a purchase; a missing
            // invoice was deleted. Both leave the selector cleared and stop
            // auto-suggestion, but the hint copy differs.
            this.invoiceMissing.set(!rejected);
            this.userClearedInvoice = true;
            this.form.patchValue({ invoice_id: '' });
          }
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