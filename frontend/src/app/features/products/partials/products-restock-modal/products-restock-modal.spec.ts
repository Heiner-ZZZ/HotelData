import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import { ProductsApiService } from '../../services/products-api.service';
import type { HotelProduct } from '../../models/products.model';
import { ProductsRestockModalComponent } from './products-restock-modal';

const PRODUCT: HotelProduct = {
  productId: 'PROD-AGUA01',
  propId: 1,
  name: 'Agua Mineral',
  description: 'Botella 500ml',
  category: 'Bebidas',
  type: 'retail',
  costPrice: 1.5,
  unitPrice: 3,
  quantityAvailable: 5,
  defaultSupplier: null,
  supplierSku: null,
  parLevel: null,
  lastPurchaseInvoiceRef: null,
  lastPurchaseQty: null,
  lastPurchaseAt: null,
  isActive: true,
  archivedAt: null,
  archivedBy: null,
  createdAt: '2026-08-01T00:00:00Z',
  updatedAt: '2026-08-01T00:00:00Z',
};

function invoiceFixture(count: number, vendorPrefix = 'Proveedor') {
  return {
    items: Array.from({ length: count }, (_, i) => ({
      id: `INV-ID-${i + 1}`,
      vendor_name: `${vendorPrefix} ${i + 1}`,
      category: 'Suministros',
      description: '',
      amount: 100 + i,
      tax_amount: 16,
      total: 116 + i,
      status: 'pending',
      invoice_date: `2026-08-0${i + 1}`,
      due_date: '2026-09-01',
      created_at: '2026-08-01T00:00:00Z',
    })),
    total: count,
    page: 1,
    page_size: 20,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  };
}

describe('ProductsRestockModalComponent', () => {
  async function setup(overrides?: { invoiceCount?: number; product?: HotelProduct }) {
    const restockProduct = jest.fn().mockReturnValue(of({
      product_id: 'PROD-AGUA01',
      prop_id: 1,
      quantity_available: 8,
      cost_price: 2.1,
      default_supplier: 'Acme',
      last_purchase_invoice_ref: null,
      last_purchase_qty: 3,
      total_cost: 6.3,
      ledger_journal_id: 'JRN-1',
      updated_at: '2026-08-06T00:00:00Z',
      updated_by: 'admin_test',
    }));
    const navigate = jest.fn();

    await TestBed.configureTestingModule({
      imports: [ProductsRestockModalComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PropertyContextService, useValue: { currentPropId: () => 1 } },
        { provide: ProductsApiService, useValue: { restockProduct } },
        { provide: Router, useValue: { navigate } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ProductsRestockModalComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('product', overrides?.product ?? PRODUCT);
    fixture.detectChanges(); // runs ngOnInit → fires the invoices GET

    const httpTesting = TestBed.inject(HttpTestingController);
    const invoiceReq = httpTesting.expectOne((req) => req.url.includes('/expenses/invoices'));
    expect(invoiceReq.request.params.get('prop_id')).toBe('1');
    // Rejected invoices must never be offered as a purchase source: the GET
    // carries the allow-list of statuses the selector may show.
    expect(invoiceReq.request.params.get('status')).toBe('pending,approved,paid');
    const count = overrides?.invoiceCount ?? 2;
    invoiceReq.flush(invoiceFixture(count));

    // Auto-selecting a supplier-matching invoice fires the inverse-link
    // detail GET synchronously inside the flush handler. Drain it so
    // supplier-matching tests don't leak an unflushed request (a future
    // `httpTesting.verify()` in afterEach would break them). The list URL
    // also contains '/expenses/invoices' but was already consumed above.
    httpTesting.match((req) =>
      req.url.includes('/expenses/invoices/') && !req.url.includes('page='));

    return { fixture, component, restockProduct, httpTesting, navigate };
  }

  it('loads the current hotel invoices into the selector', async () => {
    const { component } = await setup();
    expect(component.invoicesLoading()).toBe(false);
    expect(component.invoicesError()).toBeNull();
    expect(component.invoices().length).toBe(2);
    expect(component.invoices()[0].id).toBe('INV-ID-1');
    expect(component.invoices()[0].vendorName).toBe('Proveedor 1');
  });

  it('sends the selected invoice id as the real FK reference', async () => {
    const { component, restockProduct } = await setup();

    component.form.patchValue({ qty: 3, unit_cost: 2.1, invoice_id: 'INV-ID-2' });
    component.submit();

    expect(restockProduct).toHaveBeenCalledWith(1, 'PROD-AGUA01', {
      qty: 3,
      unit_cost: 2.1,
      supplier_name: undefined,
      invoice_id: 'INV-ID-2',
    });
  });

  it('omits invoice_id when no invoice is selected', async () => {
    const { component, restockProduct } = await setup();

    component.form.patchValue({ qty: 1, unit_cost: 2.0, invoice_id: '' });
    component.submit();

    expect(restockProduct).toHaveBeenCalledWith(1, 'PROD-AGUA01', {
      qty: 1,
      unit_cost: 2.0,
      supplier_name: undefined,
      invoice_id: undefined,
    });
  });

  it('clears a stale invoice link when the backend rejects it (400)', async () => {
    const { component, restockProduct } = await setup();
    const err = new Error('Factura de gasto no encontrada para esta propiedad') as any;
    err.status = 400;
    err.error = { detail: 'Factura de gasto no encontrada para esta propiedad' };
    restockProduct.mockReturnValue(throwError(() => err));

    component.form.patchValue({ qty: 1, unit_cost: 2.0, invoice_id: 'INV-ID-1' });
    component.submit();

    expect(component.invoiceMissing()).toBe(true);
    expect(component.form.get('invoice_id')?.value).toBe('');
    expect(component.submitError()).toContain('Factura');
  });

  it('keeps the invoice link on a non-invoice 400 (e.g. validation)', async () => {
    const { component, restockProduct } = await setup();
    const err = new Error('qty debe ser > 0') as any;
    err.status = 400;
    err.error = { detail: 'qty debe ser > 0' };
    restockProduct.mockReturnValue(throwError(() => err));

    component.form.patchValue({ qty: 1, unit_cost: 2.0, invoice_id: 'INV-ID-1' });
    component.submit();

    // A validation 400 must NOT drop the user's invoice selection.
    expect(component.invoiceMissing()).toBe(false);
    expect(component.form.get('invoice_id')?.value).toBe('INV-ID-1');
  });

  it('flags a rejected invoice distinctly from a missing one (400)', async () => {
    const { component, restockProduct } = await setup();
    const err = new Error('La factura está rechazada y no puede usarse como fuente de compra') as any;
    err.status = 400;
    err.error = { detail: 'La factura está rechazada y no puede usarse como fuente de compra' };
    restockProduct.mockReturnValue(throwError(() => err));

    component.form.patchValue({ qty: 1, unit_cost: 2.0, invoice_id: 'INV-ID-1' });
    component.submit();

    // The invoice EXISTS but is rejected — different hint than 'ya no existe'.
    expect(component.invoiceRejected()).toBe(true);
    expect(component.invoiceMissing()).toBe(false);
    expect(component.form.get('invoice_id')?.value).toBe('');
  });

  it('auto-selects the most recent invoice from the same supplier as the product', async () => {
    const productWithSupplier: HotelProduct = { ...PRODUCT, defaultSupplier: 'Proveedor 1' };
    const { component } = await setup({ product: productWithSupplier, invoiceCount: 2 });

    expect(component.suggestedInvoice()).not.toBeNull();
    expect(component.suggestedInvoice()?.id).toBe('INV-ID-1');
    expect(component.form.get('invoice_id')?.value).toBe('INV-ID-1');
  });

  it('does not override a manual invoice choice even when the supplier matches', async () => {
    const productWithSupplier: HotelProduct = { ...PRODUCT, defaultSupplier: 'Proveedor 1' };
    const { component } = await setup({ product: productWithSupplier, invoiceCount: 2 });

    // The user picks a different invoice AFTER the auto-suggestion landed.
    component.form.patchValue({ invoice_id: 'INV-ID-2' });
    component.form.patchValue({ supplier_name: 'Proveedor 1' });

    expect(component.form.get('invoice_id')?.value).toBe('INV-ID-2');
    // And submit keeps the manual choice, not the suggested one.
    const v = component.form.getRawValue();
    expect(v.invoice_id).toBe('INV-ID-2');
  });

  it('suggests nothing when the supplier matches no invoice', async () => {
    const productWithSupplier: HotelProduct = { ...PRODUCT, defaultSupplier: 'Otro Proveedor' };
    const { component } = await setup({ product: productWithSupplier, invoiceCount: 2 });

    expect(component.suggestedInvoice()).toBeNull();
    expect(component.form.get('invoice_id')?.value).toBe('');
  });

  it('live-suggests when the user types a supplier matching an invoice after load', async () => {
    // Product without a supplier → nothing auto-selected on load.
    const { component } = await setup({ invoiceCount: 2 });
    expect(component.suggestedInvoice()).toBeNull();
    expect(component.form.get('invoice_id')?.value).toBe('');

    // User types a supplier that matches INV-ID-2 (Proveedor 2).
    component.form.patchValue({ supplier_name: 'Proveedor 2' });

    expect(component.suggestedInvoice()?.id).toBe('INV-ID-2');
    expect(component.form.get('invoice_id')?.value).toBe('INV-ID-2');
  });

  it('does not fight an intentional Sin factura reset while the supplier still matches', async () => {
    const productWithSupplier: HotelProduct = { ...PRODUCT, defaultSupplier: 'Proveedor 1' };
    const { component } = await setup({ product: productWithSupplier, invoiceCount: 2 });
    expect(component.form.get('invoice_id')?.value).toBe('INV-ID-1');

    // The user deliberately clears the selection to 'Sin factura'.
    component.form.patchValue({ invoice_id: '' });
    // A supplier keystroke must NOT re-select it against the user's will.
    component.form.patchValue({ supplier_name: 'Proveedor 1' });

    expect(component.form.get('invoice_id')?.value).toBe('');
  });

  describe('inverse link: selected invoice already restocked this product', () => {
    function detailFixture(id = 'INV-ID-1', productLines: any[] = []) {
      return {
        id,
        vendor_name: 'Proveedor 1',
        category: 'Suministros',
        description: '',
        amount: 100,
        tax_amount: 16,
        total: 116,
        status: 'pending',
        invoice_date: '2026-08-01',
        due_date: '2026-09-01',
        approved_by: null,
        approved_at: null,
        notes: '',
        prop_id: 1,
        product_lines: productLines,
        created_at: '2026-08-01T00:00:00Z',
        updated_at: '2026-08-01T00:00:00Z',
      };
    }

    it('shows a notice with qty and date when the selected invoice already restocked this product', async () => {
      const { component, fixture, httpTesting } = await setup();

      component.form.patchValue({ invoice_id: 'INV-ID-1' });
      const detailReq = httpTesting.expectOne((req) => req.url.includes('/expenses/invoices/INV-ID-1'));
      detailReq.flush(detailFixture('INV-ID-1', [
        { product_id: 'PROD-AGUA01', name: 'Agua Mineral', qty: 4, unit_cost: 1.5, line_total: 6, restocked: true, stock_now: 55, cost_now: 1.5 },
      ]));
      await fixture.whenStable();
      await Promise.resolve();
      fixture.detectChanges();

      const line = component.alreadyRestockedLine();
      expect(line).not.toBeNull();
      expect(line?.qty).toBe(4);
      expect(component.invoiceDetail()?.invoiceDate).toBe('2026-08-01');
      const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
      expect(text).toContain('Ya fue repuesto');
      expect(text).toContain('4');
      expect(text).toContain('2026-08-01');
    });

    it('shows no notice when the selected invoice never restocked this product', async () => {
      const { component, fixture, httpTesting } = await setup();

      component.form.patchValue({ invoice_id: 'INV-ID-2' });
      const detailReq = httpTesting.expectOne((req) => req.url.includes('/expenses/invoices/INV-ID-2'));
      detailReq.flush(detailFixture('INV-ID-2', [
        { product_id: 'PROD-OTRO', name: 'Otro Producto', qty: 2, unit_cost: 9, line_total: 18, restocked: true, stock_now: 3, cost_now: 9 },
      ]));
      await fixture.whenStable();
      await Promise.resolve();
      fixture.detectChanges();

      expect(component.alreadyRestockedLine()).toBeNull();
      expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Ya fue repuesto');
    });

    it('renders the notice as an inverse link to the invoice detail page', async () => {
      const { component, fixture, httpTesting, navigate } = await setup();

      component.form.patchValue({ invoice_id: 'INV-ID-1' });
      const detailReq = httpTesting.expectOne((req) => req.url.includes('/expenses/invoices/INV-ID-1'));
      detailReq.flush(detailFixture('INV-ID-1', [
        { product_id: 'PROD-AGUA01', name: 'Agua Mineral', qty: 4, unit_cost: 1.5, line_total: 6, restocked: true, stock_now: 55, cost_now: 1.5 },
      ]));
      await fixture.whenStable();
      await Promise.resolve();
      fixture.detectChanges();

      const link = (fixture.nativeElement as HTMLElement).querySelector('.already-restocked');
      expect(link).not.toBeNull();
      expect(link?.textContent).toContain('Ver factura');

      component.openInvoiceDetail(new Event('click'));
      expect(navigate).toHaveBeenCalledWith(
        ['/management/expenses/invoices', 'INV-ID-1'],
        { queryParams: { prop_id: 1 } },
      );
    });
  });
});
