import { mapProduct } from './products-api.service';

describe('mapProduct', () => {
  it('maps a resolved last purchase invoice (real FK) to the domain model', () => {
    const product = mapProduct({
      product_id: 'PROD-AGUA01',
      prop_id: 1,
      name: 'Agua Mineral',
      description: 'Botella 500ml',
      unit_price: 3,
      quantity_available: 55,
      category: 'Bebidas',
      type: 'retail',
      cost_price: 3.25,
      last_purchase_invoice_ref: '6a75728bb699cdd287776161',
      last_purchase_invoice: {
        id: '6a75728bb699cdd287776161',
        vendor_name: 'Distribuidora Lima',
        invoice_date: '2026-08-06',
        due_date: '2026-09-06',
        total: 13,
        status: 'pending',
      },
      is_active: true,
      created_at: '2026-08-01T00:00:00Z',
      updated_at: '2026-08-06T00:00:00Z',
    });

    expect(product.lastPurchaseInvoice).toEqual({
      id: '6a75728bb699cdd287776161',
      vendorName: 'Distribuidora Lima',
      invoiceDate: '2026-08-06',
      dueDate: '2026-09-06',
      total: 13,
      status: 'pending',
    });
    // The raw ref is preserved alongside the resolved invoice.
    expect(product.lastPurchaseInvoiceRef).toBe('6a75728bb699cdd287776161');
  });

  it('maps null when there is no linked invoice (legacy free-text ref)', () => {
    const product = mapProduct({
      product_id: 'PROD-SNACK1',
      prop_id: 1,
      name: 'Snack Bar',
      description: '',
      unit_price: 5,
      quantity_available: 20,
      category: 'Snacks',
      type: 'retail',
      last_purchase_invoice_ref: 'INV-001',
      is_active: true,
      created_at: '',
      updated_at: '',
    });

    expect(product.lastPurchaseInvoice).toBeNull();
    expect(product.lastPurchaseInvoiceRef).toBe('INV-001');
  });

  it('maps null when the server sends no invoice field at all', () => {
    const product = mapProduct({
      product_id: 'P1',
      prop_id: 1,
      name: 'Sin compras',
      description: '',
      unit_price: 1,
      quantity_available: 0,
      category: 'Otros',
      is_active: true,
    });

    expect(product.lastPurchaseInvoice).toBeNull();
    expect(product.lastPurchaseInvoiceRef).toBeNull();
  });
});

import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_CONFIG } from '../../../core/api/api.config';
import { ProductsApiService } from './products-api.service';

/**
 * Migración E (2026-08): los line-items de reserva exigen prop_id en query
 * (gate por-hotel + pertenencia del booking). El cliente lo envía.
 */
describe('ProductsApiService line-items (Migración E: prop_id en query)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_CONFIG, useValue: { baseUrl: '/api' } },
      ],
    });
    return {
      service: TestBed.inject(ProductsApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('getLineItems envía prop_id en query', () => {
    const { service, httpMock } = setup();
    service.getLineItems('BK-1', 5).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/management/products/bookings/BK-1/line-items' && r.method === 'GET',
    );
    expect(req.request.params.get('prop_id')).toBe('5');
    req.flush({ items: [] });
  });

  it('addLineItem envía prop_id en query', () => {
    const { service, httpMock } = setup();
    service.addLineItem('BK-1', { product_id: 'P1', name: 'Spa', unit_price: 10, quantity: 1 } as never, 5).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/management/products/bookings/BK-1/line-items' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('5');
    req.flush({});
  });
});
