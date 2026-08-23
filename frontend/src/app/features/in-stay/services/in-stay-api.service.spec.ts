import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { InStayApiService } from './in-stay-api.service';

/**
 * Migración E (2026-08): las operaciones del staff inbox exigen ``prop_id``
 * en el QUERY (gate por-hotel + pertenencia de sesión/request/conversación).
 * El cliente lo envía siempre — estos tests pinchan el contrato.
 */
describe('InStayApiService staff (Migración E: prop_id en query)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    return {
      service: TestBed.inject(InStayApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('getMyStaySession envía prop_id en query', () => {
    const { service, httpMock } = setup();
    service.getMyStaySession('BK-1', 5).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/stay/my-session' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('5');
    expect(req.request.body).toEqual({ booking_id: 'BK-1' });
    req.flush({});
  });

  it('staffReply envía prop_id en query', () => {
    const { service, httpMock } = setup();
    service.staffReply('101', 'Hola', 5).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/stay/conversations/101/reply' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('5');
    req.flush({});
  });

  it('createSession envía prop_id en query (además del body)', () => {
    const { service, httpMock } = setup();
    service.createSession({
      booking_id: 'BK-1',
      prop_id: 5,
      room_label: '101',
      guest_name: 'X',
      check_in: '2026-08-22',
      check_out: '2026-08-23',
    }).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/stay/sessions' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('5');
    req.flush({});
  });
});
