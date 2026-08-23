import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AmenitiesApiService } from './amenities-api.service';

/**
 * Migración E (2026-08): ``PUT /api/management/amenities`` y
 * ``/special-requests`` exigen ``prop_id`` en el QUERY (gate por-hotel +
 * consistencia query↔body) — el body solo respondía 400.
 */
describe('AmenitiesApiService save (Migración E: prop_id en query)', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    return {
      service: TestBed.inject(AmenitiesApiService),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('saveAmenities envía prop_id en query Y en body', () => {
    const { service, httpMock } = setup();
    const payload = { prop_id: 2, active_amenities: ['Spa'] } as never;
    service.saveAmenities(payload).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/management/amenities' && r.method === 'PUT',
    );
    expect(req.request.params.get('prop_id')).toBe('2');
    expect(req.request.body).toEqual(payload);
    req.flush({});
  });

  it('saveSpecialRequests envía prop_id en query', () => {
    const { service, httpMock } = setup();
    const payload = { prop_id: 2, special_requests: [], high_floor_from: 3 } as never;
    service.saveSpecialRequests(payload).subscribe();

    const req = httpMock.expectOne(
      (r) => r.url === '/management/amenities/special-requests' && r.method === 'PUT',
    );
    expect(req.request.params.get('prop_id')).toBe('2');
    req.flush({});
  });
});
