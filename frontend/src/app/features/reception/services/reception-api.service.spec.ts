import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_CONFIG } from '../../../core/api/api.config';
import { ReceptionApiService } from './reception-api.service';

/**
 * Migración E (2026-08): ``POST /api/reception/shifts/open`` exige
 * ``prop_id`` en el QUERY (gate por-hotel ``require_prop_permission``) y
 * valida consistencia query↔body (400 si no coinciden). El cliente envía
 * prop_id en ambos — estos tests pinchan el contrato para que el body-only
 * no regrese (el hueco del middleware que dejó el banner con 400).
 */
describe('ReceptionApiService openShift (Migración E: prop_id en query)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_CONFIG, useValue: { baseUrl: '/api' } },
      ],
    });
    return {
      service: TestBed.inject(ReceptionApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('openShift envía prop_id en query Y en body', () => {
    const { service, httpMock } = setup();
    service.openShift({
      prop_id: 3,
      shift_type: 'morning',
      employee: 'Juan Pérez',
      cash_initial: 500,
    }).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/reception/shifts/open' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('3');
    expect(req.request.body).toEqual({
      prop_id: 3,
      shift_type: 'morning',
      employee: 'Juan Pérez',
      cash_initial: 500,
    });
    req.flush({ message: 'Turno abierto', shift: { id: 's1', prop_id: 3 } });
  });
});
