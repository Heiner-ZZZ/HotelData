import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import { ReservationActionService } from '../../services/reservation-action.service';
import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { InStayApiService } from '../../../in-stay/services/in-stay-api.service';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { ReservationDetailPageComponent } from './reservation-detail-page';

describe('ReservationDetailPageComponent — canMarkNoShow', () => {
  /**
   * Wire-shape plana de `GET /reservations/{id}` (tras el flattening de
   * booking_orders). `stay_status` AUSENTE = reserva confirmada legacy que
   * nunca llegó a check-in — el backend ya acepta marcarla no-show, pero el
   * gate del botón exigía `stay_status === 'pending'` y la ocultaba.
   */
  const BASE_DTO: ReservationDetailDto = {
    booking_id: 'BK-1',
    prop_id: 1,
    status: 'confirmed',
    booking_source: 'web',
    guest_name: 'Guest Prueba',
    guest_email: 'guest@test.com',
    guest_phone: '',
    cedula: '',
    check_in_date: '2020-01-01',
    check_out_date: '2020-01-08',
    total_price: 658,
    currency: 'USD',
    total_nights: 7,
    rooms: 1,
    adults: 2,
    children: 0,
    comment: '',
    created_at: '2020-01-01T00:00:00Z',
    can_cancel: true,
    assigned_rooms: [],
    history: [],
    additional_charges: [],
    // stay_status deliberately absent (no check-in registered)
  } as unknown as ReservationDetailDto;

  async function renderDetail(dto: ReservationDetailDto) {
    await TestBed.configureTestingModule({
      imports: [ReservationDetailPageComponent],
      providers: [
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => 'BK-1' } },
            paramMap: of(new Map([['bookingId', 'BK-1']])),
          },
        },
        { provide: Router, useValue: { events: of(), navigate: jest.fn() } },
        { provide: ReservationsAuthService, useValue: { isStaff: () => true, isClient: () => false } },
        { provide: OperationModeService, useValue: { reset: jest.fn(), setMode: jest.fn(), setTransientMode: () => () => {} } },
        { provide: ConfirmDialogService, useValue: { open: jest.fn(() => Promise.resolve(true)) } },
        { provide: ReservationActionService, useValue: { confirm: jest.fn(() => of({})), reject: jest.fn(() => of({})) } },
        { provide: InStayApiService, useValue: { getMyStaySession: jest.fn(() => of({ token: 't' })) } },
        { provide: ProductsApiService, useValue: {} },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReservationDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url === '/reservations/BK-1');
    req.flush(dto);

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, component, httpTesting };
  }

  it('habilita Marcar no-show para confirmada SIN stay_status cuyo check-in ya pasó', async () => {
    const { component } = await renderDetail(BASE_DTO);
    expect(component.canMarkNoShow()).toBe(true);
  });

  it('habilita Marcar no-show para confirmada con stay_status pending y check-in pasado', async () => {
    const { component } = await renderDetail({
      ...BASE_DTO,
      stay_status: 'pending',
    } as unknown as ReservationDetailDto);
    expect(component.canMarkNoShow()).toBe(true);
  });

  it('NO habilita para reservas ya checked_in', async () => {
    const { component } = await renderDetail({
      ...BASE_DTO,
      stay_status: 'checked_in',
    } as unknown as ReservationDetailDto);
    expect(component.canMarkNoShow()).toBe(false);
  });

  it('NO habilita si el check-in todavía no llegó', async () => {
    const { component } = await renderDetail({
      ...BASE_DTO,
      check_in_date: '2099-01-01',
      check_out_date: '2099-01-08',
    } as unknown as ReservationDetailDto);
    expect(component.canMarkNoShow()).toBe(false);
  });
});
