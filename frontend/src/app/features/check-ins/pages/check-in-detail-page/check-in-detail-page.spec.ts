import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { NoShowService, type NoShowResult } from '../../../../shared/services/no-show.service';
import { CheckInsApiService, type CheckInDetailDto } from '../../services/check-ins-api.service';
import { CheckInDetailPageComponent } from './check-in-detail-page';

describe('CheckInDetailPageComponent', () => {
  const DETAIL: CheckInDetailDto = {
    booking_id: 'BK-1',
    prop_id: 1,
    hotel_label: 'Hotel Lima Centro',
    guest_name: 'Guest Prueba',
    guest_email: 'guest@test.com',
    guest_phone: '',
    cedula: '',
    check_in_date: '2026-08-09',
    check_in_date_actual: null,
    check_in_time_actual: null,
    estimated_arrival_time: '',
    late_checkin: false,
    check_out_date: '2026-08-11',
    total_price: 218,
    currency: 'USD',
    total_nights: 2,
    rooms: 1,
    adults: 2,
    children: 0,
    status: 'confirmed',
    stay_status: '',
    room_type_id: 'RT-1',
    room_type_name: 'Habitación Standard',
    folio: null,
    check_in_by: null,
    payment_method: '',
    booking_source: 'web',
    comment: '',
    assigned_rooms: [],
    check_in_arrival_time: '',
    check_in_has_companions: false,
    check_in_companions_count: 0,
    check_in_document_verified: false,
    check_in_keys_delivered: false,
    check_in_payment_pending: false,
    check_in_deposit_received: false,
    check_in_privacy_signed: false,
    check_in_observations: '',
  };

  async function renderDetail(dto: CheckInDetailDto, opts?: { hasPermission?: boolean }) {
    const hasPermission = jest.fn(() => opts?.hasPermission ?? true);
    await TestBed.configureTestingModule({
      imports: [CheckInDetailPageComponent],
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
        { provide: Router, useValue: { events: of() } },
        { provide: ToastService, useValue: { error: jest.fn() } },
        { provide: AuthService, useValue: { hasPermission } },
        { provide: NoShowService, useValue: { markNoShowWithConfirm: jest.fn(), successMessage: jest.fn() } },
        { provide: CheckInsApiService, useValue: {} },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(CheckInDetailPageComponent);
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    req.flush(dto);

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, component: fixture.componentInstance, httpTesting };
  }
  async function render403() {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await TestBed.configureTestingModule({
      imports: [CheckInDetailPageComponent],
      providers: [
        // Incluir el interceptor real para probar el camino vivo: el 403 llega
        // como ApiError plano ({ status, message }), no como HttpErrorResponse.
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => 'BK-1' } },
            paramMap: of(new Map([['bookingId', 'BK-1']])),
          },
        },
        { provide: Router, useValue: { events: of() } },
        { provide: ToastService, useValue: { error: jest.fn() } },
        { provide: AuthService, useValue: { hasPermission: jest.fn(() => true) } },
        { provide: NoShowService, useValue: { markNoShowWithConfirm: jest.fn(), successMessage: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(CheckInDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    req.flush({ detail: 'Permiso requerido: check-ins.read' }, { status: 403, statusText: 'Forbidden' });

    // httpResource asienta el error en un microtask (promise interna); esperar
    // a que el estado 'forbidden' y los efectos se asienten antes de leer.
    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, component, consoleSpy, httpTesting };
  }

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('data() devuelve null sin lanzar cuando el detalle responde 403', async () => {
    const { component } = await render403();
    expect(() => component.data()).not.toThrow();
    expect(component.data()).toBeNull();
  });

  it('viewState pasa a forbidden en 403 y la página muestra el aviso de permiso', async () => {
    const { fixture, component } = await render403();
    expect(component.viewState()).toBe('forbidden');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('permiso');
  });

  it('no spamea la consola tras el 403 y los computeds derivados no lanzan', async () => {
    const { component, consoleSpy } = await render403();
    expect(() => component.totalPrice()).not.toThrow();
    expect(() => component.assignedRoomsStatuses()).not.toThrow();
    expect(() => component.totalNights()).not.toThrow();
    expect(consoleSpy).not.toHaveBeenCalled();
  });

  // ═══ No-show: check-in bloqueado ═══
  // Fechas en hora LOCAL (toISOString() usa UTC y puede desfasar el día).
  function localDateStr(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  it('bloquea el check-in de una reserva marcada no_show', async () => {
    const { fixture, component } = await renderDetail({ ...DETAIL, stay_status: 'no_show' });
    expect(component.noShow()).toBe(true);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('no-show');
    // El wizard no se renderiza (ni el botón Continuar ni los pasos).
    expect(text).not.toContain('Continuar');
    // La vista de completado tampoco: un no-show no es un check-in hecho.
    expect(text).not.toContain('Check-In Completado');
  });

  it('bloquea el check-in cuando la fecha de check-out ya pasó (no-show por vencimiento)', async () => {
    const past = new Date();
    past.setDate(past.getDate() - 1);
    const pastStr = localDateStr(past);
    const { fixture, component } = await renderDetail({
      ...DETAIL,
      stay_status: '',
      check_in_date: pastStr,
      check_out_date: pastStr,
    });
    expect(component.noShow()).toBe(true);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('no-show');
    expect(text).not.toContain('Continuar');
    expect(text).not.toContain('Check-In Completado');
  });

  it('no bloquea una reserva vigente con check-in hoy', async () => {
    const today = new Date();
    const todayStr = localDateStr(today);
    const future = new Date();
    future.setDate(future.getDate() + 2);
    const { fixture, component } = await renderDetail({
      ...DETAIL,
      stay_status: '',
      check_in_date: todayStr,
      check_out_date: localDateStr(future),
    });
    expect(component.noShow()).toBe(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).not.toContain('no-show');
  });

  // ═══ Botón 'Marcar no-show' (cierre manual desde recepción) ═══
  function pastDetail(): CheckInDetailDto {
    const past = new Date();
    past.setDate(past.getDate() - 2);
    const pastStr = localDateStr(past);
    return { ...DETAIL, stay_status: '', check_in_date: pastStr, check_out_date: pastStr };
  }

  function findNoShowButton(fixture: { nativeElement: HTMLElement }): HTMLButtonElement | undefined {
    return Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (b) => (b.textContent ?? '').includes('Marcar no-show'),
    );
  }

  it('muestra el botón Marcar no-show en el panel de bloqueo con permiso reservations.update', async () => {
    const { fixture, component } = await renderDetail(pastDetail());
    expect(component.canMarkNoShow()).toBe(true);
    expect(findNoShowButton(fixture)).toBeDefined();
  });

  it('NO muestra el botón cuando la reserva ya está marcada no_show', async () => {
    const { fixture, component } = await renderDetail({ ...pastDetail(), stay_status: 'no_show' });
    expect(component.noShow()).toBe(true);
    expect(component.canMarkNoShow()).toBe(false);
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('NO muestra el botón sin permiso reservations.update', async () => {
    const { fixture } = await renderDetail(pastDetail(), { hasPermission: false });
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('marca no-show tras confirmar: llama al NoShowService compartido, muestra folio + enlace a Facturación y oculta el botón', async () => {
    const RESULT: NoShowResult = {
      ok: true, booking_id: 'BK-1', penalty_amount: 94, check_in_date: '2026-08-01', folio_number: 'FL-NS-BK-20260',
    };
    const { fixture, component, httpTesting } = await renderDetail(pastDetail());
    const noShow = TestBed.inject(NoShowService);
    (noShow.markNoShowWithConfirm as jest.Mock).mockResolvedValue(RESULT);
    (noShow.successMessage as jest.Mock).mockImplementation(
      (r: NoShowResult) => `No-show registrado. Se cobró $${r.penalty_amount.toFixed(2)} como penalización.`,
    );

    findNoShowButton(fixture)!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(noShow.markNoShowWithConfirm).toHaveBeenCalledWith('BK-1', 'Guest Prueba');
    expect(component.successMessage()).toContain('No-show registrado');
    expect(component.successMessage()).toContain('94.00');
    expect(component.noShowResult()).toEqual({ folio_number: 'FL-NS-BK-20260', penalty_amount: 94 });

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('FL-NS-BK-20260');
    expect(text).toContain('Ver folio en Facturación');
    const folioLink = (fixture.nativeElement as HTMLElement).querySelector('a.ciw-noshow-folio-link');
    expect(folioLink).not.toBeNull();

    // Tras recargar con stay_status=no_show (estado real en backend) el botón desaparece
    const reloadReq = httpTesting.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    reloadReq.flush({ ...pastDetail(), stay_status: 'no_show' });
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();
    expect(component.canMarkNoShow()).toBe(false);
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('no llama al servicio si el usuario cancela la confirmación', async () => {
    const { fixture, component } = await renderDetail(pastDetail());
    const noShow = TestBed.inject(NoShowService);
    (noShow.markNoShowWithConfirm as jest.Mock).mockResolvedValue(null);

    component.markNoShow();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.noShowResult()).toBeNull();
    expect(component.successMessage()).toBe('');
  });
});
