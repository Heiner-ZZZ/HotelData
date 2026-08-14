import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { BillingApiService } from '../../services/billing-api.service';
import { LinkShiftModalComponent } from './link-shift-modal';
import type { PaymentLinkCandidates } from '../../models/billing.model';

describe('LinkShiftModalComponent', () => {
  function setup(candidates$: unknown = of({
    payment: {
      id: 'P-1', bookingId: 'BK-1', invoiceId: null, refundId: null, refundDocumentId: null,
      refundDocumentNumber: null, reconciliationStatus: null, reconciliationReason: null,
      amount: 50, method: 'cash', status: 'confirmed', reference: 'PAY-LEGACY-1', paidAt: '2026-08-06 10:00',
      shiftId: null, shiftEmployee: null, shiftOpenedBy: null, shiftType: null,
      refundShiftId: null, refundShiftEmployee: null,
    },
    shifts: [],
  })) {
    const api = {
      getPaymentLinkCandidates: jest.fn(() => candidates$),
      linkPaymentToShift: jest.fn(() => of({})),
    } as unknown as BillingApiService;

    TestBed.configureTestingModule({
      imports: [LinkShiftModalComponent],
      providers: [{ provide: BillingApiService, useValue: api }],
    });

    const fixture = TestBed.createComponent(LinkShiftModalComponent);
    fixture.componentRef.setInput('paymentId', 'P-1');
    fixture.componentRef.setInput('propId', 1);
    fixture.componentRef.setInput('paymentReference', 'PAY-LEGACY-1');
    fixture.detectChanges();
    fixture.detectChanges(); // dispara ngOnInit tras setInput
    return { fixture, component: fixture.componentInstance, api };
  }

  const candidates: PaymentLinkCandidates = {
    payment: {
      id: 'P-1', bookingId: 'BK-1', invoiceId: null, refundId: null, refundDocumentId: null,
      refundDocumentNumber: null, reconciliationStatus: null, reconciliationReason: null,
      amount: 50, method: 'cash', status: 'confirmed', reference: 'PAY-LEGACY-1', paidAt: '2026-08-06 10:00',
      shiftId: null, shiftEmployee: null, shiftOpenedBy: null, shiftType: null,
      refundShiftId: null, refundShiftEmployee: null,
    },
    shifts: [
      {
        id: 'shift-open', propId: 1, status: 'open', shiftType: 'morning', employee: 'Carlos Pérez',
        openedBy: 'admin', startTime: '2026-08-09T13:00:00', closedAt: null,
      },
      {
        id: 'shift-closed', propId: 1, status: 'closed', shiftType: 'evening', employee: 'María Gómez',
        openedBy: 'admin', startTime: '2026-08-08T13:00:00', closedAt: '2026-08-08T21:00:00',
      },
    ],
  };

  it('carga los candidatos y preselecciona el turno abierto', () => {
    const ctx = setup(of(candidates));

    expect(ctx.api.getPaymentLinkCandidates).toHaveBeenCalledWith('P-1', 1);
    expect(ctx.component.candidates()).toHaveLength(2);
    expect(ctx.component.selectedShiftId()).toBe('shift-open');
    expect(ctx.component.loading()).toBe(false);
  });

  it('muestra error de carga cuando el API falla', () => {
    const ctx = setup(throwError(() => new Error('boom')));

    expect(ctx.component.loadError()).toBe('No se pudieron cargar los turnos del hotel.');
    expect(ctx.component.loading()).toBe(false);
  });

  it('confirma enviando el turno seleccionado y emite linked', () => {
    const ctx = setup(of(candidates));
    const linked = jest.fn();
    ctx.component.linked.subscribe(linked);

    ctx.component.selectShift('shift-closed');
    ctx.component.confirm();

    expect(ctx.api.linkPaymentToShift).toHaveBeenCalledWith('P-1', 'shift-closed', 1);
    expect(linked).toHaveBeenCalled();
  });

  it('no envía nada sin turno seleccionado y muestra error local', () => {
    const ctx = setup(of(candidates));

    ctx.component.selectedShiftId.set('');
    ctx.component.confirm();

    expect(ctx.api.linkPaymentToShift).not.toHaveBeenCalled();
    expect(ctx.component.submitError()).toBe('Selecciona un turno para vincular el pago.');
  });

  it('muestra el detalle del error del servidor al fallar el vínculo', () => {
    const ctx = setup(of(candidates));
    ctx.api.linkPaymentToShift = jest.fn(() => throwError(() => ({
      error: { detail: 'El pago ya está vinculado a un turno' },
    })));

    ctx.component.confirm();

    expect(ctx.component.submitError()).toBe('El pago ya está vinculado a un turno');
  });
});
