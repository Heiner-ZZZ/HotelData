import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';

import { CheckInsApiService } from './check-ins-api.service';
import { CheckOutsApiService } from '../../check-outs/services/check-outs-api.service';
import { PropertyContextService } from '../../../shared/services/property-context.service';
import { NoShowService } from '../../../shared/services/no-show.service';
import { ConfirmDialogService } from '../../../shared/ui/confirm-dialog/confirm-dialog.service';

/**
 * TDD seam: public HTTP boundary — cada método de management debe enviar ?prop_id.
 * Si falta, backend responde 400 `Contexto de hotel requerido` (require_prop_permission).
 * Este archivo fija el contrato para normal + early-check-in + late-check-out + no-show/reopen.
 * Antes del fix propParams() devolvía HttpParams vacío cuando currentPropId()=0
 * y detailResource no leía ?prop_id de la URL → 400 en direct-link/bookmark.
 * Después del fix propParams() prioriza context y hace fallback a window.location.search.
 */
describe('CheckIn/Out prop_id gate (normal + early + late + no-show)', () => {
  let http: HttpTestingController;

  const propCtxMock = {
    currentPropId: signal(1),
    ready: signal(true),
    currentPropLabel: signal('Hotel Lima Centro'),
    currentPropLabelShort: signal('Hotel Lima'),
    singleHotelMode: signal(false),
    defaultPropId: signal(1),
    mode: signal('all' as const),
    assignedProperties: signal([{ propId: 1, label: 'Hotel Lima Centro' }]),
  };

  const propCtxEmptyMock = {
    currentPropId: signal(0),
    ready: signal(true),
    currentPropLabel: signal(''),
    currentPropLabelShort: signal(''),
    singleHotelMode: signal(false),
    defaultPropId: signal(0),
    mode: signal('all' as const),
    assignedProperties: signal([]),
  };

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        CheckInsApiService,
        CheckOutsApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PropertyContextService, useValue: propCtxMock },
        { provide: ConfirmDialogService, useValue: { open: jest.fn(() => Promise.resolve(true)) } },
        // NoShowService necesita ConfirmDialog + PropertyContext
        NoShowService,
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('GET detail check-in incluye prop_id (normal)', () => {
    const api = TestBed.inject(CheckInsApiService);
    api.getCheckInDetail('BK-1').subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', prop_id: 1 } as never);
  });

  it('PATCH save detail check-in incluye prop_id', () => {
    const api = TestBed.inject(CheckInsApiService);
    api.saveCheckInDetail('BK-1', { check_in_observations: 'test' }).subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail') && r.method === 'PATCH');
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', updated: true } as never);
  });

  it('POST complete normal (check_in_keys_delivered + document) incluye prop_id', () => {
    const api = TestBed.inject(CheckInsApiService);
    api
      .completeCheckInWithDetail('BK-1', {
        check_in_keys_delivered: true,
        check_in_document_verified: true,
      })
      .subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/complete') && r.method === 'POST');
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.body).toEqual(expect.objectContaining({ check_in_keys_delivered: true }));
    req.flush({ booking_id: 'BK-1', stay_status: 'checked_in' } as never);
  });

  it('POST complete early-check-in (early_approved) incluye prop_id + motivo + fee', () => {
    const api = TestBed.inject(CheckInsApiService);
    api
      .completeCheckInWithDetail('BK-1', {
        check_in_keys_delivered: true,
        check_in_document_verified: true,
        early_check_in_mode: 'early_approved',
        early_check_in_approved: true,
        early_check_in_reason: 'Habitación lista',
        early_check_in_fee: 25,
      })
      .subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/complete'));
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.body).toEqual(
      expect.objectContaining({
        early_check_in_mode: 'early_approved',
        early_check_in_reason: 'Habitación lista',
        early_check_in_fee: 25,
      }),
    );
    req.flush({ booking_id: 'BK-1', stay_status: 'checked_in' } as never);
  });

  it('GET room-availability para early-check-in incluye prop_id', () => {
    const api = TestBed.inject(CheckInsApiService);
    api.validateRoomAvailability('BK-1').subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/room-availability'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', all_available: true, rooms: [], issues: [], validated_at: '' } as never);
  });

  it('POST declare-late-arrival incluye prop_id', () => {
    const api = TestBed.inject(CheckInsApiService);
    api.declareLateArrival('BK-1', { declared_late_arrival: true, estimated_arrival_time: '02:00' }).subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-ins/BK-1/declare-late-arrival'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', declared_late_arrival: true } as never);
  });

  it('POST reopen-no-show (gerente) incluye prop_id', () => {
    const api = TestBed.inject(CheckInsApiService);
    api.reopenNoShow('BK-1', 'Llegó tarde').subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/bookings/BK-1/reopen-no-show'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ ok: true } as never);
  });

  it('POST no-show (NoShowService) incluye prop_id explícito de d.prop_id', () => {
    const svc = TestBed.inject(NoShowService);
    // Pasa propId explícito 1 (como hace check-in-detail-page con d.prop_id)
    svc.markNoShow('BK-1', 1).subscribe();
    const req = http.expectOne((r) => r.url === '/management/bookings/BK-1/no-show');
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ ok: true, booking_id: 'BK-1', penalty_amount: 0, check_in_date: '', folio_number: null } as never);
  });

  it('GET detail check-out incluye prop_id (normal)', () => {
    const api = TestBed.inject(CheckOutsApiService);
    api.getCheckOutDetail('BK-1').subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-outs/BK-1/detail'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', prop_id: 1 } as never);
  });

  it('PATCH save detail check-out incluye prop_id', () => {
    const api = TestBed.inject(CheckOutsApiService);
    api.saveCheckOutDetail('BK-1', { check_out_observations: 'ok' }).subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-outs/BK-1/detail') && r.method === 'PATCH');
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1' } as never);
  });

  it('POST complete check-out normal incluye prop_id', () => {
    const api = TestBed.inject(CheckOutsApiService);
    api.completeCheckOutWithDetail('BK-1', { check_out_keys_returned: true }).subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-outs/BK-1/complete'));
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1', stay_status: 'checked_out' } as never);
  });

  it('POST complete late-check-out (late_approved) incluye prop_id + motivo', () => {
    const api = TestBed.inject(CheckOutsApiService);
    api
      .completeCheckOutWithDetail('BK-1', {
        late_checkout_mode: 'late_approved',
        late_checkout_approved: true,
        late_checkout_reason: 'Vuelo tarde',
        late_checkout_fee: 30,
      })
      .subscribe();
    const req = http.expectOne((r) => r.url.includes('/management/check-outs/BK-1/complete'));
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.body).toEqual(
      expect.objectContaining({
        late_checkout_mode: 'late_approved',
        late_checkout_reason: 'Vuelo tarde',
      }),
    );
    req.flush({ booking_id: 'BK-1', stay_status: 'checked_out' } as never);
  });

  it('fallback a ?prop_id de la URL cuando currentPropId()=0 (direct-link)', () => {
    // Reconfigura TestBed con contexto vacío y simula URL con ?prop_id=1
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        CheckInsApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PropertyContextService, useValue: propCtxEmptyMock },
        { provide: ConfirmDialogService, useValue: { open: jest.fn(() => Promise.resolve(true)) } },
        NoShowService,
      ],
    });
    // jsdom window.location es http://localhost/ → inyectamos ?prop_id=1 vía history
    window.history.pushState({}, '', '/?prop_id=1');
    const http2 = TestBed.inject(HttpTestingController);
    const api = TestBed.inject(CheckInsApiService);
    api.getCheckInDetail('BK-1').subscribe();
    const req = http2.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    // Debe tomar de URL aunque contexto sea 0
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({ booking_id: 'BK-1' } as never);
    http2.verify();
    // Limpia URL para no contaminar otros tests
    window.history.pushState({}, '', '/');
  });
});
