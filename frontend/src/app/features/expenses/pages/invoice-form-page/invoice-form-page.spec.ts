import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { InvoiceFormPageComponent } from './invoice-form-page';

describe('InvoiceFormPageComponent', () => {
  async function setup() {
    const createInvoice = jest.fn().mockReturnValue(of({}));
    const navigate = jest.fn();

    await TestBed.configureTestingModule({
      imports: [InvoiceFormPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PropertyContextService, useValue: { mode: () => 'single', currentPropId: () => 1 } },
        { provide: ExpensesApiService, useValue: { createInvoice } },
        { provide: Router, useValue: { navigate, events: of(null) } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(InvoiceFormPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges(); // fires the products httpResource

    const httpTesting = TestBed.inject(HttpTestingController);
    const productsReq = httpTesting.expectOne((req) => req.url.includes('/management/products/hotels/1'));
    productsReq.flush({
      items: [
        { product_id: 'PROD-AGUA01', prop_id: 1, name: 'Agua Mineral', description: '',
          unit_price: 3, quantity_available: 50, category: 'Bebidas', type: 'retail',
          cost_price: 1.5, is_active: true, created_at: '', updated_at: '' },
        { product_id: 'PROD-SNACK1', prop_id: 1, name: 'Snack Bar', description: '',
          unit_price: 5, quantity_available: 20, category: 'Snacks', type: 'retail',
          cost_price: 2.5, is_active: true, created_at: '', updated_at: '' },
      ],
    });
    fixture.detectChanges();

    return { fixture, component, createInvoice, navigate, httpTesting };
  }

  it('loads the hotel products into the line selector', async () => {
    const { component } = await setup();
    expect(component.products().length).toBe(2);
    expect(component.products()[0].name).toBe('Agua Mineral');
  });

  it('auto-computes the amount from added lines and sends product_lines', async () => {
    const { component, createInvoice } = await setup();

    component.form.vendorName = 'Distribuidora Lima';
    component.lineForm = { productId: 'PROD-AGUA01', qty: 3, unitCost: 2.1 };
    component.addLine();
    component.lineForm = { productId: 'PROD-SNACK1', qty: 2, unitCost: 5 };
    component.addLine();

    expect(component.productLines().length).toBe(2);
    expect(component.form.amount).toBe(16.3); // 6.30 + 10.00

    component.submit();
    expect(createInvoice).toHaveBeenCalledWith(expect.objectContaining({
      vendor_name: 'Distribuidora Lima',
      amount: 16.3,
      prop_id: 1,
      product_lines: [
        { product_id: 'PROD-AGUA01', qty: 3, unit_cost: 2.1 },
        { product_id: 'PROD-SNACK1', qty: 2, unit_cost: 5 },
      ],
    }));
  });

  it('removing a line recomputes the amount', async () => {
    const { component } = await setup();

    component.lineForm = { productId: 'PROD-AGUA01', qty: 3, unitCost: 2.1 };
    component.addLine();
    component.lineForm = { productId: 'PROD-SNACK1', qty: 2, unitCost: 5 };
    component.addLine();
    component.removeLine(0);

    expect(component.productLines().length).toBe(1);
    expect(component.form.amount).toBe(10);
  });

  it('declares INSERT mode so the nav chip shows the page is creating', async () => {
    await setup();
    const opMode = TestBed.inject(OperationModeService);
    expect(opMode.mode()).toBe('insert');
  });

  it('without lines uses the manual amount and sends no product_lines', async () => {
    const { component, createInvoice } = await setup();

    component.form.vendorName = 'Acme';
    component.form.amount = 120;
    component.form.taxAmount = 19.2;
    component.submit();

    expect(createInvoice).toHaveBeenCalledWith(expect.objectContaining({
      vendor_name: 'Acme',
      amount: 120,
      tax_amount: 19.2,
    }));
    const payload = createInvoice.mock.calls[0][0] as Record<string, unknown>;
    expect(payload.product_lines).toBeUndefined();
  });
});
