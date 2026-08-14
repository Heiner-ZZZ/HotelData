import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { firstValueFrom } from 'rxjs';

import { ConfirmDialogService } from '../ui/confirm-dialog/confirm-dialog.service';
import { NoShowService, type NoShowResult } from './no-show.service';

describe('NoShowService', () => {
  const RESULT: NoShowResult = {
    ok: true,
    booking_id: 'BK-1',
    penalty_amount: 94,
    check_in_date: '2026-08-01',
    folio_number: 'FL-NS-BK-20260',
  };

  let service: NoShowService;
  let httpTesting: HttpTestingController;
  let confirmOpen: jest.Mock;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfirmDialogService, useValue: { open: jest.fn(() => Promise.resolve(true)) } },
      ],
    });
    service = TestBed.inject(NoShowService);
    httpTesting = TestBed.inject(HttpTestingController);
    confirmOpen = TestBed.inject(ConfirmDialogService).open as jest.Mock;
  });

  afterEach(() => {
    httpTesting.verify();
  });

  it('POSTea /management/bookings/{id}/no-show y devuelve folio + penalización', async () => {
    const promise = firstValueFrom(service.markNoShow('BK-1'));

    const req = httpTesting.expectOne((r) => r.method === 'POST' && r.url === '/management/bookings/BK-1/no-show');
    expect(req.request.body).toEqual({});
    req.flush(RESULT);

    expect(await promise).toEqual(RESULT);
  });

  it('markNoShowWithConfirm: si el operador cancela → null y NO hay POST', async () => {
    confirmOpen.mockResolvedValue(false);

    const result = await service.markNoShowWithConfirm('BK-1', 'Horuz');

    expect(result).toBeNull();
    expect(confirmOpen).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Marcar no-show',
        confirmLabel: 'Marcar no-show',
        variant: 'danger',
        mode: 'delete',
      }),
    );
    httpTesting.expectNone((r) => r.method === 'POST');
  });

  it('markNoShowWithConfirm: si confirma → POST y devuelve el resultado', async () => {
    const promise = service.markNoShowWithConfirm('BK-1', 'Horuz');

    expect(confirmOpen).toHaveBeenCalledWith(
      expect.objectContaining({
        message: expect.stringContaining('Horuz'),
        modeDetail: 'Reserva BK-1',
      }),
    );

    // El POST se dispara tras resolver la promesa del diálogo (microtask).
    await Promise.resolve();
    await Promise.resolve();

    const req = httpTesting.expectOne((r) => r.method === 'POST' && r.url === '/management/bookings/BK-1/no-show');
    req.flush(RESULT);

    expect(await promise).toEqual(RESULT);
  });

  it('successMessage formatea la penalización y el caso sin monto', () => {
    expect(service.successMessage(RESULT)).toBe('No-show registrado. Se cobró $94.00 como penalización.');
    expect(
      service.successMessage({ ...RESULT, penalty_amount: 0, folio_number: null }),
    ).toBe('No-show registrado.');
  });
});
