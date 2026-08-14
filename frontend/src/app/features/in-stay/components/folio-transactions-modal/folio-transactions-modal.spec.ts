import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import type { FolioPosting, FolioPostingsResponse, LedgerFolio } from '../../../expenses/models/ledger.model';
import { FolioTransactionsModalComponent } from './folio-transactions-modal';

@Component({
  standalone: true,
  imports: [FolioTransactionsModalComponent],
  template: `
    @if (folio(); as f) {
      <app-folio-transactions-modal [folio]="f" (close)="closed.set(true)" />
    }
  `,
})
class HostComponent {
  readonly folio = signal<LedgerFolio | null>(null);
  readonly closed = signal(false);
}

describe('FolioTransactionsModalComponent', () => {
  const folio: LedgerFolio = {
    propId: 1,
    folioId: 'FOLIO-1',
    folioRef: 'FL-202608-0001',
    guestName: 'Test Guest',
    room: '110',
    checkIn: '',
    checkOut: '',
    balance: 50,
    transactionCount: 2,
    bookingId: 'BK-1',
    status: 'open',
  };

  function setup(postings: FolioPosting[]) {
    const api = {
      getFolioPostings: jest.fn(() => of<FolioPostingsResponse>({
        folioId: 'FOLIO-1',
        folioRef: 'FL-202608-0001',
        guestName: 'Test Guest',
        postings,
      })),
    } as unknown as ExpensesApiService;

    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: ExpensesApiService, useValue: api }],
    });

    const fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.folio.set(folio);
    fixture.detectChanges();
    return { fixture };
  }

  it('muestra el chip de turno/empleado en postings con atribución', () => {
    const { fixture } = setup([{
      postingId: 'P-1',
      type: 'payment',
      category: 'Pago',
      concept: 'Pago adelantado',
      amount: 50,
      quantity: 1,
      unitPrice: 50,
      referenceId: 'PAY-1',
      referenceType: 'payment',
      postedAt: '2026-08-09T10:00:00',
      shiftId: 'shift-1',
      shiftEmployee: 'Carlos Pérez',
      shiftOpenedBy: 'gerente1',
      shiftType: 'morning',
    }]);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Carlos Pérez');
    const chip = el.querySelector('.tx-shift-chip');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute('title')).toContain('shift-1');
    expect(chip?.getAttribute('title')).toContain('morning');
  });

  it('no muestra chip cuando el posting no tiene turno', () => {
    const { fixture } = setup([{
      postingId: 'P-2',
      type: 'room',
      category: 'Habitación',
      concept: 'Habitación Standard',
      amount: 120,
      quantity: 1,
      unitPrice: 120,
      referenceId: 'room-1',
      referenceType: 'room',
      postedAt: '2026-08-09T10:00:00',
    }]);

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.tx-shift-chip')).toBeNull();
    expect(el.textContent).not.toContain('Turno');
  });
});
