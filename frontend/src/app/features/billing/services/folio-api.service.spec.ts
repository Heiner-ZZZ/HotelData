import { getFolioCloseState, getFolioReconciliationNote, mapFolio, type FolioDto } from './folio-api.service';

describe('getFolioCloseState', () => {
  it('blocks closing an open folio with a positive balance', () => {
    expect(getFolioCloseState({ status: 'open', totalDue: 103 })).toBe('balance_due');
  });

  it('allows closing an open folio with zero balance', () => {
    expect(getFolioCloseState({ status: 'open', totalDue: 0 })).toBe('ready');
  });

  it('calculates the same unbilled gap used by the check-out reconciliation note', () => {
    expect(getFolioReconciliationNote({
      hasInvoice: true,
      invoiceId: 'invoice-1',
      invoiceNumber: 'INV-001',
      invoiceStatus: 'issued',
      invoiceCoveredSubtotal: 200,
      totalRoom: 200,
      totalCharges: 50,
      totalDiscounts: 0,
    })).toEqual({ invoiceNumber: 'INV-001', gap: 50 });
  });

  it('does not warn when complementary invoices cover the live folio subtotal', () => {
    expect(getFolioReconciliationNote({
      hasInvoice: true,
      invoiceId: 'invoice-1',
      invoiceNumber: 'INV-001',
      invoiceStatus: 'issued',
      invoiceCoveredSubtotal: 250,
      totalRoom: 200,
      totalCharges: 50,
      totalDiscounts: 0,
    })).toBeNull();
  });

  it('does not warn for a cancelled invoice', () => {
    expect(getFolioReconciliationNote({
      hasInvoice: true,
      invoiceId: 'invoice-1',
      invoiceNumber: 'INV-001',
      invoiceStatus: 'cancelled',
      invoiceCoveredSubtotal: 200,
      totalRoom: 200,
      totalCharges: 50,
      totalDiscounts: 0,
    })).toBeNull();
  });

  it('maps invoice coverage metadata for the printed folio', () => {
    const view = mapFolio({
      id: 'folio-coverage', folio_number: 'FL-202608-0002', booking_id: 'BK-2', prop_id: 1,
      guest_name: 'Guest', guest_email: '', room_label: '101', hotel_label: 'Hotel',
      check_in_date: '2026-08-01', check_out_date: '2026-08-02', status: 'closed',
      is_expired: false, has_invoice: true, total_room: 200, total_charges: 50,
      total_discounts: 0, total_payments: 0, total_due: 250,
      invoice_number: 'INV-001', invoice_status: 'issued', invoice_subtotal: 200,
      invoice_covered_subtotal: 200, postings: [], posting_count: 1,
      created_at: '2026-08-01', closed_at: '2026-08-02', closed_by: 'staff', invoice_id: 'invoice-1',
    } as FolioDto);

    expect(view.invoiceNumber).toBe('INV-001');
    expect(view.invoiceCoveredSubtotal).toBe(200);
    expect(getFolioReconciliationNote(view)).toEqual({ invoiceNumber: 'INV-001', gap: 50 });
  });

  it('maps a historically reopened folio for the collection UI', () => {
    const view = mapFolio({
      id: 'folio-1', folio_number: 'FL-202608-0001', booking_id: 'BK-1', prop_id: 1,
      guest_name: 'Guest', guest_email: '', room_label: '101', hotel_label: 'Hotel',
      check_in_date: '2026-08-01', check_out_date: '2026-08-02', status: 'open',
      close_reason: null, is_expired: true, has_invoice: false, total_room: 100,
      total_charges: 10, total_discounts: 0, total_payments: 0, total_due: 110,
      postings: [], posting_count: 1, created_at: '2026-08-01', closed_at: '2026-08-02',
      closed_by: 'staff', reopened_at: '2026-08-08T12:00:00Z', reopened_by: 'historical_reconciliation',
      invoice_id: null,
      settlement_payment_id: 'payment-1', settlement_payment_ids: ['payment-1'], settlement_event_id: 'event-1', settlement_event_ids: ['event-1'], settlement_shift_id: 'shift-1', settlement_shift_ids: ['shift-1'],
      settlement_invoice_id: 'invoice-1', settlement_evidence_type: 'manager_attestation',
      settlement_evidence_reference: 'TRACE-1', settled_recorded_at: '2026-08-08T12:01:00Z',
    } as FolioDto);

    expect(view.reopenedAt).toBe('2026-08-08T12:00:00Z');
    expect(view.settlementPaymentId).toBe('payment-1');
    expect(view.settlementPaymentIds).toEqual(['payment-1']);
    expect(view.settlementEventId).toBe('event-1');
    expect(view.settlementEventIds).toEqual(['event-1']);
    expect(view.settlementShiftId).toBe('shift-1');
    expect(view.settlementShiftIds).toEqual(['shift-1']);
    expect(view.settlementInvoiceId).toBe('invoice-1');
    expect(view.settlementEvidenceReference).toBe('TRACE-1');
    expect(view.status).toBe('open');
    expect(getFolioCloseState(view)).toBe('balance_due');
  });
});
