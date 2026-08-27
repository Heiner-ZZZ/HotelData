import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ReservationsApiService } from './reservations-api.service';

/**
 * Los POST de reserva que golpean rutas por-hotel del backend deben mandar
 * ``prop_id`` como QUERY param. El dependency ``require_prop_permission``
 * resuelve el hotel solo de path/query y deniega con 400
 * ("Contexto de hotel requerido (prop_id).") si no lo encuentra; el body
 * (``_check_body_prop_id``) no le sirve. Sin esto, validar cupón, pasar al
 * paso de revisión (preview) y guardar (create) devolvían 400.
 */
describe('ReservationsApiService — contexto de hotel en los POST de reserva', () => {
  let service: ReservationsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ReservationsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function expectPropIdQuery(urlPart: string, propId: string) {
    const req = http.expectOne((r) => r.url.includes(urlPart) && r.method === 'POST');
    expect(req.request.params.get('prop_id')).toBe(propId);
    return req;
  }

  /** El body del request ya viene serializado como objeto en HttpTestingController. */
  function bodyOf(req: { request: { body: unknown } }): Record<string, unknown> {
    return (req.request.body ?? {}) as Record<string, unknown>;
  }

  it('validateCoupon envía prop_id por QUERY (además del body)', () => {
    service.validateCoupon('VERANO20', 1).subscribe();

    const req = expectPropIdQuery('/reservations/validate-coupon', '1');
    expect(bodyOf(req)).toMatchObject({ coupon_code: 'VERANO20', prop_id: 1 });

    req.flush({ valid: true, message: 'Código válido', discount_percent: 20 });
  });

  it('previewReservation envía prop_id por QUERY (pasar al paso 2)', () => {
    service.previewReservation({ propId: 1 } as never).subscribe();

    const req = expectPropIdQuery('/reservations/preview', '1');
    expect(bodyOf(req)).toMatchObject({ prop_id: 1 });

    req.flush({});
  });

  it('createReservation envía prop_id por QUERY (guardar la reserva)', () => {
    service.createReservation({ propId: 1 } as never).subscribe();

    const req = expectPropIdQuery('/reservations', '1');
    expect(bodyOf(req)).toMatchObject({ prop_id: 1 });

    req.flush({});
  });
});
