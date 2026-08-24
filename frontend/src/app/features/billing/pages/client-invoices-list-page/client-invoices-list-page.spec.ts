import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import type { InvoicesListViewModel } from '../../models/billing.model';
import { BillingApiService } from '../../services/billing-api.service';
import { ClientInvoicesListPageComponent } from './client-invoices-list-page';

function viewModel(): InvoicesListViewModel {
  return {
    items: [
      {
        id: 'inv-1',
        bookingId: 'BK-20260807202628-71E570F9',
        invoiceNumber: 'INV-202608-0002',
        subtotal: 162.07,
        taxes: 25.93,
        total: 188.0,
        status: 'issued',
        issuedAt: '2026-08-07T20:26:28Z',
        paidAt: null,
      },
    ],
    total: 1,
    page: 1,
    pageSize: 10,
    hasPrev: false,
    hasNext: false,
    totalPages: 1,
  };
}

describe('ClientInvoicesListPageComponent — datos sensibles y copy', () => {
  async function render() {
    const billingApi = { getMyInvoices: jest.fn().mockReturnValue(of(viewModel())) };

    await TestBed.configureTestingModule({
      imports: [ClientInvoicesListPageComponent],
      providers: [
        { provide: BillingApiService, useValue: billingApi },
        { provide: ActivatedRoute, useValue: { queryParamMap: of(new Map([['page', '1']])) } },
        { provide: Router, useValue: { navigate: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ClientInvoicesListPageComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    return { fixture, billingApi };
  }

  it('NO expone datos bancarios sensibles (banco/cuenta/CLABE) al huésped', async () => {
    const { fixture } = await render();
    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('INV-202608-0002');
    expect(rendered).not.toContain('Banco HotelData');
    expect(rendered).not.toContain('CLABE');
    expect(rendered).not.toContain('6460 1802 3004 7812');
    fixture.destroy();
  });

  it('no usa la palabra "simulado" en ninguna parte de la lista de facturas', async () => {
    const { fixture } = await render();
    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered.toLowerCase()).not.toContain('simulado');
    fixture.destroy();
  });
});
