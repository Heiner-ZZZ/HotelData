import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { signal } from '@angular/core';

import { CheckInsApiService } from './check-ins-api.service';
import { PropertyContextService } from '../../../shared/services/property-context.service';

describe('CheckInsApiService.completeCheckIn', () => {
  let service: CheckInsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        CheckInsApiService,
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(1),
            ready: signal(true),
            currentPropLabel: signal('Hotel Lima Centro'),
            currentPropLabelShort: signal('Hotel Lima'),
            singleHotelMode: signal(false),
            defaultPropId: signal(1),
            mode: signal('all' as const),
            assignedProperties: signal([{ propId: 1, label: 'Hotel Lima Centro' }]),
          },
        },
      ],
    });
    service = TestBed.inject(CheckInsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('completa el check-in rápido declarando express (el listado no captura el checklist manual)', () => {
    service.completeCheckIn('BK-EXPRESS-1').subscribe();

    const req = http.expectOne((r) => r.url === '/management/check-ins/BK-EXPRESS-1/complete');
    expect(req.request.method).toBe('POST');
    expect(req.request.params.get('prop_id')).toBe('1');
    // El quick-action del listado es un flujo express: omite llaves/documento
    // por diseño (el checklist se completa después en el detalle). Sin
    // express:true el endpoint responde 422.
    expect(req.request.body).toEqual({ express: true });
    req.flush({ ok: true });
  });
});
