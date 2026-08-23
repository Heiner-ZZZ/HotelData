import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_CONFIG } from '../../../core/api/api.config';
import { HrApiService } from './hr-api.service';

/**
 * Fix B (2026-08): el portal HR es una feature POR-HOTEL — el backend exige
 * ``prop_id`` en el query (``require_prop_permission``, deny-by-default sin
 * asignación). El cliente debe enviarlo: estos tests pinchan el contrato
 * de ``getPortal`` / ``getPortalTasks`` (prop_id SIEMPRE presente cuando se
 * conoce el hotel).
 *
 * Migración E (2026-08): ``shiftCheckIn`` / ``shiftCheckOut`` pasaron de
 * ``require_any_permission`` GLOBAL a ``require_any_prop_permission``
 * (prop_id obligatorio en query + 404 si el turno pertenece a otro hotel).
 * El cliente envía prop_id cuando lo conoce (query ?prop_id= o el del
 * empleado logueado).
 */
describe('HrApiService portal (Fix B: contexto de hotel)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_CONFIG, useValue: { baseUrl: '/api' } },
      ],
    });
    return {
      service: TestBed.inject(HrApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('getPortal envía prop_id y week_start al backend', () => {
    const { service, httpMock } = setup();
    service.getPortal('emp-1', '2026-08-17', 1).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/portal/emp-1' && r.method === 'GET',
    );
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.params.get('week_start')).toBe('2026-08-17');
    req.flush({ employee: {}, kpis: {}, payroll: {}, weekly_roster: [], recent_events: [] });
  });

  it('getPortal sin prop_id no lo envía (el backend responde 400)', () => {
    const { service, httpMock } = setup();
    service.getPortal('emp-1').subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/portal/emp-1' && r.method === 'GET',
    );
    expect(req.request.params.get('prop_id')).toBeNull();
    req.flush({ employee: {}, kpis: {}, payroll: {}, weekly_roster: [], recent_events: [] });
  });

  it('getPortalTasks envía prop_id al backend', () => {
    const { service, httpMock } = setup();
    service.getPortalTasks('emp-1', 1).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/portal/emp-1/tasks' && r.method === 'GET',
    );
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({});
  });

  it('shiftCheckIn envía prop_id al backend (gate por-hotel)', () => {
    const { service, httpMock } = setup();
    service.shiftCheckIn('shift-1', 'emp-1', 'llegó a tiempo', 1).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/shifts/shift-1/check-in' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.body).toEqual({
      employee_id: 'emp-1',
      notes: 'llegó a tiempo',
    });
    req.flush({ shift_id: 'shift-1', status: 'active', check_in: '2026-08-22T10:00:00Z' });
  });

  it('shiftCheckIn sin prop_id no lo envía (el backend responde 400)', () => {
    const { service, httpMock } = setup();
    service.shiftCheckIn('shift-1', 'emp-1').subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/shifts/shift-1/check-in' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBeNull();
    req.flush({ shift_id: 'shift-1', status: 'active', check_in: '2026-08-22T10:00:00Z' });
  });

  it('shiftCheckOut envía prop_id al backend', () => {
    const { service, httpMock } = setup();
    service.shiftCheckOut('shift-1', 'emp-1', undefined, 2).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/hr/shifts/shift-1/check-out' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('2');
    req.flush({ shift_id: 'shift-1', status: 'completed', check_out: '2026-08-22T18:00:00Z' });
  });
});
