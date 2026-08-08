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
