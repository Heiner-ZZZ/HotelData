import { getFolioCloseState, mapFolio, type FolioDto } from './folio-api.service';

describe('getFolioCloseState', () => {
  it('blocks closing an open folio with a positive balance', () => {
    expect(getFolioCloseState({ status: 'open', totalDue: 103 })).toBe('balance_due');
  });

  it('allows closing an open folio with zero balance', () => {
    expect(getFolioCloseState({ status: 'open', totalDue: 0 })).toBe('ready');
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
});
