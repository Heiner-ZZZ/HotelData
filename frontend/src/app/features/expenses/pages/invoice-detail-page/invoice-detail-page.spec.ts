import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';

import { InvoiceDetailPageComponent } from './invoice-detail-page';

describe('InvoiceDetailPageComponent', () => {
  async function setup(detailPayload: Record<string, unknown>, propId = 1) {
    const navigate = jest.fn();

    await TestBed.configureTestingModule({
      imports: [InvoiceDetailPageComponent],
      providers: [
        // Interceptor real: los errores llegan como ApiError plano (camino vivo).
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        { provide: ToastService, useValue: { error: jest.fn() } },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => '6a75728bb699cdd287776161' } },
            paramMap: of(new Map([['invoiceId', '6a75728bb699cdd287776161']])),
          },
        },
        { provide: Router, useValue: { navigate, events: of() } },
        { provide: PropertyContextService, useValue: { currentPropId: signal(propId) } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(InvoiceDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const detailReq = httpTesting.expectOne((req) =>
      req.url.includes('/api/hotels/1/vendor-ap/invoices/6a75728bb699cdd287776161'));
    detailReq.flush(detailPayload);
    // httpResource asienta su valor en un microtask (promise interna) — esperar
    // a que el computed inv() lo recoja antes de leer el DOM.
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, component, navigate, httpTesting };
  }

  const baseInvoice = {
    id: '6a75728bb699cdd287776161',
    vendor_name: 'Distribuidora Lima',
    category: 'Suministros',
    description: '',
    amount: 13,
    tax_amount: 0,
    total: 13,
    status: 'pending',
    invoice_date: '2026-08-01',
    due_date: '2026-09-01',
    approved_by: null,
    approved_at: null,
    notes: '',
    prop_id: 1,
    created_at: '2026-08-01T10:00:00Z',
    updated_at: '2026-08-01T10:00:00Z',
  };

  it('renders payment reference and journal trace for a paid vendor bill', async () => {
    const { fixture } = await setup({
      ...baseInvoice,
      status: 'paid',
      payment_method: 'bank_transfer',
      payment_reference: 'VB-PAY-001',
      payment_journal_id: 'JE-20260808-0001',
    });

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('VB-PAY-001');
    expect(text).toContain('JE-20260808-0001');
  });

  it('uses the dedicated payment flow for an approved vendor bill', async () => {
    const { component, httpTesting } = await setup({ ...baseInvoice, status: 'approved' });

    component.payInvoice(baseInvoice.id);

    const paymentReq = httpTesting.expectOne((req) =>
      req.url.includes('/api/expenses/invoices/6a75728bb699cdd287776161/pay')
      && req.method === 'POST',
    );
    expect(paymentReq.request.body).toEqual({
      method: 'bank_transfer',
      payment_reference: 'UI-6a75728bb699cdd287776161',
    });
    paymentReq.flush({ ...baseInvoice, status: 'paid' });
  });

  it('does not offer payment before a pending vendor bill is approved', async () => {
    const { fixture } = await setup(baseInvoice);

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Aprobar');
    expect(text).not.toContain('Marcar Pagada');
  });

  it('maps product lines with live stock into the reverse view', async () => {
    const { component, fixture } = await setup({
      ...baseInvoice,
      product_lines: [
        {
          product_id: 'PROD-FC925A95',
          name: 'Daño mayor (pared/ventana)',
          qty: 4,
          unit_cost: 3.25,
          line_total: 13,
          restocked: true,
          stock_now: 55,
          cost_now: 3.25,
        },
      ],
    });

    const lines = component.productLines();
    expect(lines.length).toBe(1);
    expect(lines[0].productId).toBe('PROD-FC925A95');
    expect(lines[0].qty).toBe(4);
    expect(lines[0].unitCost).toBe(3.25);
    expect(lines[0].lineTotal).toBe(13);
    expect(lines[0].stockNow).toBe(55);
    expect(lines[0].restocked).toBe(true);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Restocks vinculados');
    expect(el.textContent).toContain('Daño mayor');
    expect(el.textContent).toContain('Stock actual: 55');
    expect(el.textContent).toContain('4 uds');
  });

  it('no lines renders no restock section', async () => {
    const { component, fixture } = await setup(baseInvoice);
    expect(component.productLines().length).toBe(0);
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Restocks vinculados');
  });

  it('navigates to the product edit page with prop_id', async () => {
    const { component, navigate } = await setup({
      ...baseInvoice,
      product_lines: [
        {
          product_id: 'PROD-FC925A95', name: 'Daño mayor', qty: 4,
          unit_cost: 3.25, line_total: 13, restocked: true,
          stock_now: 55, cost_now: 3.25,
        },
      ],
    });

    const line = component.productLines()[0];
    expect(component.productHref(line)).toBe('/management/products/PROD-FC925A95/edit?prop_id=1');
    component.openProduct(new Event('click'), line);
    expect(navigate).toHaveBeenCalledWith(
      ['/management/products', 'PROD-FC925A95', 'edit'],
      { queryParams: { prop_id: 1 } },
    );
  });

  it('renders an Ir al inventario button that navigates to the product list with prop_id', async () => {
    const { component, fixture, navigate } = await setup({
      ...baseInvoice,
      product_lines: [
        {
          product_id: 'PROD-FC925A95', name: 'Daño mayor', qty: 4,
          unit_cost: 3.25, line_total: 13, restocked: true,
          stock_now: 55, cost_now: 3.25,
        },
      ],
    });

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ir al inventario');

    component.goToInventory();
    expect(navigate).toHaveBeenCalledWith(['/management/products'], {
      queryParams: { prop_id: 1 },
    });
  });

  it('mapea un 404 real (ApiError del interceptor) al estado empty', async () => {
    const { fixture, component, httpTesting } = await setup(baseInvoice, 1);

    // setup() ya resolvió el detalle con éxito; recargamos y simulamos un 404.
    component.detailResource.reload();
    fixture.detectChanges();
    const notFound = httpTesting.expectOne((req) =>
      req.url.includes('/api/hotels/1/vendor-ap/invoices/6a75728bb699cdd287776161'));
    notFound.flush({ detail: 'No encontrada' }, { status: 404, statusText: 'Not Found' });

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    // En vivo el interceptor convierte el error a ApiError; el viewState debe
    // leer el status igual y reportar 'empty' (no 'error').
    expect(component.viewState()).toBe('empty');
  });

  it('flags a failed restock line with fallback fields when stock is null', async () => {
    const { component, fixture } = await setup({
      ...baseInvoice,
      product_lines: [
        {
          product_id: 'PROD-GONE', name: 'Producto borrado', qty: 2,
          unit_cost: 4, line_total: 8, restocked: false,
          stock_now: null, cost_now: null,
        },
      ],
    });

    const line = component.productLines()[0];
    expect(line.restocked).toBe(false);
    expect(line.stockNow).toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('falló');
    expect(text).toContain('Stock actual: —');
  });
});
