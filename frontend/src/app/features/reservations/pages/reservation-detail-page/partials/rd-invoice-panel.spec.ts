import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { RdInvoicePanelComponent } from './rd-invoice-panel';

/** View-model del detalle de reserva (misma forma que ReservationDetailViewModel). */
function vm(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    stayStatus: 'pending',
    noShowPenaltyAmount: null,
    noShowPenaltyPercent: null,
    noShowFolioNumber: null,
    invoice: {
      id: 'inv-1',
      invoiceNumber: 'INV-202608-0002',
      subtotal: 162.07,
      taxes: 25.93,
      total: 188.0,
      status: 'issued',
    },
    ...overrides,
  };
}

describe('RdInvoicePanelComponent — fuente de verdad del no-show', () => {
  async function render(data: Record<string, unknown>) {
    await TestBed.configureTestingModule({
      imports: [RdInvoicePanelComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    const fixture = TestBed.createComponent(RdInvoicePanelComponent);
    fixture.componentRef.setInput('vm', data);
    fixture.detectChanges();
    return fixture;
  }

  it('para una reserva normal muestra la factura de la estadía con Pagar ahora', async () => {
    const fixture = await render(vm());
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Facturación');
    expect(text).toContain('INV-202608-0002');
    expect(text).toContain('Pagar ahora');
    fixture.destroy();
  });

  it('para un no-show muestra la penalización como lo que se debe pagar, sin Pagar ahora', async () => {
    const fixture = await render(vm({
      stayStatus: 'no_show',
      noShowPenaltyAmount: 47.94,
      noShowPenaltyPercent: 51,
      noShowFolioNumber: 'FL-NS-1',
    }));
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Penalización por no-show');
    expect(text).toContain('$47.94');
    expect(text).toContain('51% de 1 noche');
    expect(text).toContain('FL-NS-1');
    expect(text).not.toContain('Pagar ahora');
    expect(text).not.toContain('Pendiente de pago');
    fixture.destroy();
  });
});
