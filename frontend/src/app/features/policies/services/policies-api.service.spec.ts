import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_CONFIG } from '../../../core/api/api.config';
import { PoliciesApiService } from './policies-api.service';

/**
 * Migración E (2026-08): ``PUT /api/management/policies`` exige ``prop_id``
 * en el QUERY (gate por-hotel ``require_prop_permission`` + consistencia
 * query↔body) — el body solo respondía 400. Estos tests pinchan el contrato.
 */
describe('PoliciesApiService savePolicies (Migración E: prop_id en query)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: API_CONFIG, useValue: { baseUrl: '/api' } },
      ],
    });
    return {
      service: TestBed.inject(PoliciesApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('savePolicies envía prop_id en query Y en body', () => {
    const { service, httpMock } = setup();
    const payload = { prop_id: 7, check_in_time: '15:00', check_out_time: '12:00' } as never;
    service.savePolicies(payload).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/api/management/policies' && r.method === 'PUT',
    );
    expect(req.request.params.get('prop_id')).toBe('7');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });
});
