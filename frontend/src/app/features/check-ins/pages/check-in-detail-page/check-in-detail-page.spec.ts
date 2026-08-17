import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { NoShowService, type NoShowResult } from '../../../../shared/services/no-show.service';
import {
  CheckInsApiService,
  type CheckInDetailDto,
  type LateArrivalDto,
} from '../../services/check-ins-api.service';
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
    no_show_penalty_amount: null,
    no_show_reopened_at: null,
    no_show_reopened_by: '',
    no_show_reopen_reason: '',
    no_show_penalty_removed: false,
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
    const checkInApi = {
      completeCheckInWithDetail: jest.fn(() => of({ booking_id: 'BK-1', stay_status: 'checked_in', folio: 'FOL-1' })),
      declareLateArrival: jest.fn(() => of({ booking_id: 'BK-1', declared_late_arrival: false, estimated_arrival_time: '' })),
      reopenNoShow: jest.fn(() => of({ ok: true, booking_id: 'BK-1', stay_status: 'pending', penalty_amount: 0, folio_number: null, penalty_removed: false })),
    };
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
        { provide: CheckInsApiService, useValue: checkInApi },
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

    return { fixture, component: fixture.componentInstance, httpTesting, checkInApi };
  }
  async function render403() {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => undefined);

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

  it('mantiene deshabilitado el check-in y explica que una reserva futura aún no está disponible', async () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const futureDate = localDateStr(tomorrow);
    const { fixture, component } = await renderDetail({
      ...DETAIL,
      check_in_date: futureDate,
      check_out_date: localDateStr(new Date(tomorrow.getFullYear(), tomorrow.getMonth(), tomorrow.getDate() + 2)),
    });

    component.goToStep(5);
    fixture.detectChanges();

    expect(component.isFutureDate()).toBe(true);
    const button = Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (candidate) => (candidate.textContent ?? '').includes('Realizar Check-In'),
    ) as HTMLButtonElement | undefined;
    expect(button).toBeDefined();
    expect(button!.disabled).toBe(true);
    expect(button!.getAttribute('aria-describedby')).toBe('ciw-future-date-help');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Disponible desde');
  });

  it('abre una confirmación explícita para cortesía y registra el modo sin mover la reserva', async () => {
    const today = new Date();
    const todayStr = localDateStr(today);
    const dto = {
      ...DETAIL,
      check_in_date: todayStr,
      check_out_date: localDateStr(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 2)),
      assigned_rooms: [{
        hotel_room_id: 'ROOM-1', room_number: '101', room_label: '101', floor: '1', room_status: 'available',
      }],
      early_check_in: {
        enabled: true,
        is_early: true,
        minutes_before: 30,
        courtesy_minutes: 60,
        requires_approval: false,
        check_in_time: '15:00',
        default_fee: 0,
      },
    } as unknown as CheckInDetailDto;
    const { fixture, component, checkInApi } = await renderDetail(dto);

    component.keysDelivered.set(true);
    component.goToStep(5);
    component.openEarlyCheckInDialog();
    await Promise.resolve();
    fixture.detectChanges();

    expect(component.earlyDialogOpen()).toBe(true);
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('cortesía');
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.activeElement?.id).toBe('ciw-early-dialog');
    expect(checkInApi.completeCheckInWithDetail).not.toHaveBeenCalled();

    component.confirmEarlyCheckIn();
    expect(checkInApi.completeCheckInWithDetail).toHaveBeenCalledWith(
      'BK-1',
      expect.objectContaining({
        early_check_in_mode: 'early_courtesy',
        early_check_in_approved: true,
        early_check_in_fee: 0,
      }),
    );
  });

  it('muestra la hora real de llegada anticipada en el detalle completado', async () => {
    const { fixture } = await renderDetail({
      ...DETAIL,
      stay_status: 'checked_in',
      folio: 'FL-EARLY-1',
      check_in_date_actual: '2026-08-14',
      check_in_time_actual: '13:00',
      early_check_in: {
        enabled: true,
        is_early: false,
        minutes_before: 0,
        courtesy_minutes: 60,
        requires_approval: false,
        check_in_time: '15:00',
        default_fee: 0,
        recorded_mode: 'early_approved',
        recorded_minutes: 120,
        recorded_fee: 25,
        approved_by: 'gerente.prueba',
        reason: 'Habitación lista',
      },
    });

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Hora real de llegada anticipada');
    expect(text).toContain('13:00 hrs');
  });

  it('exige motivo y permite cargo opcional para early check-in fuera de cortesía', async () => {
    const today = new Date();
    const todayStr = localDateStr(today);
    const dto = {
      ...DETAIL,
      check_in_date: todayStr,
      check_out_date: localDateStr(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 2)),
      assigned_rooms: [{
        hotel_room_id: 'ROOM-1', room_number: '101', room_label: '101', floor: '1', room_status: 'available',
      }],
      early_check_in: {
        enabled: true,
        is_early: true,
        minutes_before: 120,
        courtesy_minutes: 60,
        requires_approval: true,
        check_in_time: '15:00',
        default_fee: 10,
      },
    } as unknown as CheckInDetailDto;
    const { fixture, component, checkInApi } = await renderDetail(dto);

    component.keysDelivered.set(true);
    component.goToStep(5);
    component.openEarlyCheckInDialog();
    await Promise.resolve();
    fixture.detectChanges();

    expect(component.earlyDialogOpen()).toBe(true);
    component.confirmEarlyCheckIn();
    expect(component.earlyDialogError()).toContain('motivo');
    expect(checkInApi.completeCheckInWithDetail).not.toHaveBeenCalled();

    component.earlyCheckInReason.set('Habitación lista y gerente autorizó la entrega');
    component.earlyCheckInFee.set(25);
    component.confirmEarlyCheckIn();

    expect(checkInApi.completeCheckInWithDetail).toHaveBeenCalledWith(
      'BK-1',
      expect.objectContaining({
        early_check_in_mode: 'early_approved',
        early_check_in_approved: true,
        early_check_in_reason: 'Habitación lista y gerente autorizó la entrega',
        early_check_in_fee: 25,
      }),
    );
  });

  it('deja visible el motivo y deshabilita la aprobación cuando falta el permiso gerencial', async () => {
    const today = new Date();
    const todayStr = localDateStr(today);
    const dto = {
      ...DETAIL,
      check_in_date: todayStr,
      check_out_date: localDateStr(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 2)),
      assigned_rooms: [{
        hotel_room_id: 'ROOM-1', room_number: '101', room_label: '101', floor: '1', room_status: 'available',
      }],
      early_check_in: {
        enabled: true,
        is_early: true,
        minutes_before: 120,
        courtesy_minutes: 60,
        requires_approval: true,
        check_in_time: '15:00',
        default_fee: 10,
      },
    } as unknown as CheckInDetailDto;
    const { fixture, component } = await renderDetail(dto, { hasPermission: false });

    component.keysDelivered.set(true);
    component.goToStep(5);
    fixture.detectChanges();

    const button = Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (candidate) => (candidate.textContent ?? '').includes('Autorizar early check-in'),
    ) as HTMLButtonElement | undefined;
    expect(button).toBeDefined();
    expect(button!.disabled).toBe(true);
    expect(button!.getAttribute('aria-describedby')).toBe('ciw-early-approval-help');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Solo un gerente');
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

  it('mantiene el enlace al folio al volver a abrir una reserva ya marcada no-show', async () => {
    const { fixture } = await renderDetail({
      ...pastDetail(),
      stay_status: 'no_show',
      folio: 'FL-NS-BK-20260808210836-83A0CB0A',
    });

    const folioLink = (fixture.nativeElement as HTMLElement).querySelector('a.ciw-noshow-folio-link');
    expect(folioLink).not.toBeNull();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('FL-NS-BK-20260808210836-83A0CB0A');
  });

  // ═══ Llegada tardía (ventana post-medianoche) ═══
  function lateArrivalDetail(overrides: Partial<LateArrivalDto> = {}): CheckInDetailDto {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return {
      ...DETAIL,
      stay_status: '',
      check_in_date: localDateStr(yesterday),
      check_out_date: localDateStr(tomorrow),
      late_arrival: {
        guaranteed_reservation: false,
        late_arrival_cutoff: '23:59',
        no_show_execution: 'next_day',
        declared_late_arrival: false,
        protected_from_auto_no_show: false,
        is_late_arrival_window: true,
        check_in_days_ago: 1,
        blocked_reason: null,
        ...overrides,
      },
    };
  }

  it('permite el check-in de AYER dentro de la ventana de llegada tardía (fechas intactas)', async () => {
    // Drafts de tests previos podrían restaurar un step distinto.
    localStorage.clear();
    const { fixture, component } = await renderDetail(lateArrivalDetail());

    expect(component.isLateArrivalWindow()).toBe(true);
    expect(component.isPastDate()).toBe(false);
    expect(component.noShow()).toBe(false);
    // El panel explica la ventana abierta sin bloquear el wizard.
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('ventana de llegada tardía sigue abierta');
    expect(text).toContain('Continuar');
    // El botón de check-in está disponible en el paso 5 (no bloqueado por fecha pasada).
    component.keysDelivered.set(true);
    component.goToStep(5);
    fixture.detectChanges();
    expect(component.isPastDate()).toBe(false);
    const button = Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (candidate) => (candidate.textContent ?? '').includes('Realizar Check-In'),
    );
    expect(button).toBeDefined();
  });

  it('bloquea el check-in con motivo visible cuando la ventana cerró (2+ días)', async () => {
    // 3 días de retraso pero el check-out es HOY (la estadía aún no vence):
    // el caso es too_late, no el bloqueo genérico por no-show.
    const past = new Date();
    past.setDate(past.getDate() - 3);
    const today = new Date();
    const { fixture, component } = await renderDetail({
      ...DETAIL,
      stay_status: '',
      check_in_date: localDateStr(past),
      check_out_date: localDateStr(today),
      late_arrival: {
        guaranteed_reservation: false,
        late_arrival_cutoff: '23:59',
        no_show_execution: 'next_day',
        declared_late_arrival: false,
        protected_from_auto_no_show: false,
        is_late_arrival_window: false,
        check_in_days_ago: 3,
        blocked_reason: 'too_late',
      },
    });

    expect(component.isLateArrivalWindow()).toBe(false);
    expect(component.isPastDate()).toBe(true);
    expect(component.lateArrivalBlockedReason()).toBe('too_late');

    component.currentStep.set(5);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('más de un día de retraso');
  });

  it('declara llegada tardía: llama al API, muestra confirmación y recarga el detalle', async () => {
    const { fixture, component, httpTesting, checkInApi } = await renderDetail(lateArrivalDetail());
    (checkInApi.declareLateArrival as jest.Mock).mockReturnValue(
      of({ booking_id: 'BK-1', declared_late_arrival: true, estimated_arrival_time: '01:45' }),
    );

    component.openLateArrivalDeclare();
    expect(component.lateArrivalDeclareOpen()).toBe(true);
    component.lateArrivalDeclareValue.set(true);
    component.lateArrivalEta.set('01:45');
    component.saveLateArrivalDeclaration();

    expect(checkInApi.declareLateArrival).toHaveBeenCalledWith('BK-1', {
      declared_late_arrival: true,
      estimated_arrival_time: '01:45',
    });
    expect(component.successMessage()).toContain('protegida del auto no-show');

    // reload() del detalle → flush de la segunda petición para no dejar pendientes.
    await fixture.whenStable();
    fixture.detectChanges();
    const reloadReqs = httpTesting.match((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    expect(reloadReqs.length).toBe(1);
    reloadReqs[0].flush(lateArrivalDetail({ declared_late_arrival: true }));
    await fixture.whenStable();
    fixture.detectChanges();
  });

  // ═══ Reapertura de no-show (autorización de gerente) ═══
  function noShowDetail(): CheckInDetailDto {
    return {
      ...DETAIL,
      stay_status: 'no_show',
      check_in_date: localDateStr(new Date()),
      check_out_date: localDateStr(new Date()),
      folio: 'FL-NS-BK-1',
      no_show_penalty_amount: 94,
    };
  }

  function findReopenButton(fixture: { nativeElement: HTMLElement }): HTMLButtonElement | undefined {
    return Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (b) => (b.textContent ?? '').includes('Reabrir no-show'),
    );
  }

  it('muestra el botón Reabrir no-show solo con permiso gerencial sobre una reserva no_show', async () => {
    const { fixture, component } = await renderDetail(noShowDetail());
    expect(component.canReopenNoShow()).toBe(true);
    const reopenBtn = findReopenButton(fixture);
    expect(reopenBtn).toBeDefined();
    // El motivo del bloqueo está vinculado con aria-describedby.
    expect(reopenBtn!.getAttribute('aria-describedby')).toBe('ciw-noshow-reopen-help');
  });

  it('NO muestra el botón de reapertura sin el permiso gerencial', async () => {
    const { fixture, component } = await renderDetail(noShowDetail(), { hasPermission: false });
    expect(component.canReopenNoShow()).toBe(false);
    expect(findReopenButton(fixture)).toBeUndefined();
  });

  it('NO muestra el botón cuando la reserva no está marcada no_show', async () => {
    const { fixture, component } = await renderDetail({ ...DETAIL, stay_status: '' });
    expect(component.canReopenNoShow()).toBe(false);
    expect(findReopenButton(fixture)).toBeUndefined();
  });

  it('NO muestra el botón cuando el check-in tiene más de un día de retraso y explica la ventana cerrada', async () => {
    const twoDaysAgo = new Date();
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
    const { fixture, component } = await renderDetail({
      ...noShowDetail(),
      check_in_date: localDateStr(twoDaysAgo),
      check_out_date: localDateStr(new Date()),
    });
    expect(component.reopenWindowBlockedReason()).toBe('too_late');
    expect(component.canReopenNoShow()).toBe(false);
    expect(findReopenButton(fixture)).toBeUndefined();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ventana de reapertura cerrada');
    expect(text).toContain('Ajustá las fechas o creá una reserva nueva');
  });

  it('NO muestra el botón cuando la estadía ya terminó y explica que no puede reactivarse', async () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const { fixture, component } = await renderDetail({
      ...noShowDetail(),
      check_in_date: localDateStr(yesterday),
      check_out_date: localDateStr(yesterday),
    });
    expect(component.reopenWindowBlockedReason()).toBe('stay_ended');
    expect(component.canReopenNoShow()).toBe(false);
    expect(findReopenButton(fixture)).toBeUndefined();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ventana de reapertura cerrada');
    expect(text).toContain('estadía ya terminó');
  });

  it('exige motivo, llama al API con la razón y anuncia la reapertura con el folio de penalización eliminado', async () => {
    const { fixture, component, httpTesting, checkInApi } = await renderDetail(noShowDetail());
    (checkInApi.reopenNoShow as jest.Mock).mockReturnValue(
      of({ ok: true, booking_id: 'BK-1', stay_status: 'pending', penalty_amount: 94, folio_number: 'FL-NS-BK-1', penalty_removed: true, folio_deleted: true, reversal_amount: 0 }),
    );

    component.openReopenDialog();
    expect(component.reopenDialogOpen()).toBe(true);
    // El diálogo renderiza en el DOM (no quedó anidado en el wizard de check-in).
    fixture.detectChanges();
    const dlg = fixture.nativeElement.querySelector('#ciw-reopen-dialog');
    expect(dlg).not.toBeNull();
    expect(dlg!.getAttribute('role')).toBe('dialog');
    expect(dlg!.getAttribute('aria-modal')).toBe('true');

    // Sin motivo → error visible (role=alert), sin llamada al API.
    component.confirmReopenNoShow();
    expect(component.reopenError()).toContain('motivo');
    expect(checkInApi.reopenNoShow).not.toHaveBeenCalled();

    component.reopenReason.set('El huésped llegó a las 02:00; gerente autorizó la reapertura');
    component.confirmReopenNoShow();

    expect(checkInApi.reopenNoShow).toHaveBeenCalledWith('BK-1', 'El huésped llegó a las 02:00; gerente autorizó la reapertura');
    expect(component.successMessage()).toContain('Reserva reabierta');
    expect(component.successMessage()).toContain('folio de penalización se eliminó');
    expect(component.successMessage()).not.toContain('sigue en el folio');

    // reload() del detalle → flush de la segunda petición para no dejar pendientes.
    await fixture.whenStable();
    fixture.detectChanges();
    const reloadReqs = httpTesting.match((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    expect(reloadReqs.length).toBe(1);
    reloadReqs[0].flush({ ...noShowDetail(), stay_status: 'pending' });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.canReopenNoShow()).toBe(false);
  });

  it('anuncia el crédito a favor del huésped cuando el folio se conserva y la penalización se revierte', async () => {
    const { fixture, component, httpTesting, checkInApi } = await renderDetail(noShowDetail());
    (checkInApi.reopenNoShow as jest.Mock).mockReturnValue(
      of({
        ok: true,
        booking_id: 'BK-1',
        stay_status: 'pending',
        penalty_amount: 94,
        folio_number: 'FL-NS-BK-1',
        penalty_removed: true,
        folio_deleted: false,
        reversal_amount: 94,
      }),
    );

    component.openReopenDialog();
    component.reopenReason.set('El huésped llegó al día siguiente; el pago de la penalización se gestiona en Facturación');
    component.confirmReopenNoShow();

    expect(component.successMessage()).toContain('Reserva reabierta');
    expect(component.successMessage()).toContain('94.00');
    expect(component.successMessage()).toContain('crédito a favor del huésped');
    expect(component.successMessage()).toContain('FL-NS-BK-1');

    // reload() del detalle → flush de la segunda petición para no dejar pendientes.
    await fixture.whenStable();
    fixture.detectChanges();
    const reloadReqs = httpTesting.match((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    expect(reloadReqs.length).toBe(1);
    reloadReqs[0].flush({ ...noShowDetail(), stay_status: 'pending' });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.canReopenNoShow()).toBe(false);
  });

  // ═══ Marca de reapertura: el huésped llegó tras el no-show ═══
  function reopenedDetail(overrides: Partial<CheckInDetailDto> = {}): CheckInDetailDto {
    const today = new Date();
    const future = new Date();
    future.setDate(future.getDate() + 2);
    return {
      ...DETAIL,
      stay_status: 'pending',
      check_in_date: localDateStr(today),
      check_out_date: localDateStr(future),
      no_show_reopened_at: new Date().toISOString(),
      no_show_reopened_by: 'gerente.prueba',
      no_show_reopen_reason: 'El huésped llegó; gerente autorizó la reapertura',
      no_show_penalty_removed: true,
      ...overrides,
    };
  }

  it('muestra el aviso de reapertura con ventana cuando el gerente reabrió la reserva', async () => {
    const { fixture, component } = await renderDetail(reopenedDetail());
    expect(component.reopenedNotice()).not.toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Reserva reabierta tras no-show');
    expect(text).toContain('gerente.prueba');
    expect(text).toContain('El huésped llegó; gerente autorizó la reapertura');
    expect(text).toContain('La penalización del no-show fue retirada');
    expect(text).toContain('llegada tardía');
  });

  it('NO muestra el aviso en una reserva que nunca fue reabierta', async () => {
    const today = new Date();
    const future = new Date();
    future.setDate(future.getDate() + 2);
    const { fixture, component } = await renderDetail({
      ...DETAIL,
      stay_status: 'pending',
      check_in_date: localDateStr(today),
      check_out_date: localDateStr(future),
    });
    expect(component.reopenedNotice()).toBeNull();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Reserva reabierta tras no-show');
  });

  it('NO muestra el aviso cuando la ventana de reapertura ya cerró (check-in con 2+ días de retraso)', async () => {
    const twoDaysAgo = new Date();
    twoDaysAgo.setDate(twoDaysAgo.getDate() - 2);
    const { fixture, component } = await renderDetail(reopenedDetail({
      check_in_date: localDateStr(twoDaysAgo),
      check_out_date: localDateStr(new Date()),
    }));
    expect(component.reopenedNotice()).toBeNull();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Reserva reabierta tras no-show');
  });

  it('NO muestra el aviso si la reserva volvió a marcarse no_show', async () => {
    const { fixture, component } = await renderDetail(reopenedDetail({ stay_status: 'no_show' }));
    expect(component.reopenedNotice()).toBeNull();
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Reserva reabierta tras no-show');
  });

  // ═══ Gate de depósito: banner accionable ante 409 deposit_not_met ═══
  function checkinableDetail(): CheckInDetailDto {
    const today = new Date();
    const future = new Date();
    future.setDate(future.getDate() + 2);
    return {
      ...DETAIL,
      stay_status: 'pending',
      check_in_date: localDateStr(today),
      check_out_date: localDateStr(future),
      assigned_rooms: [{
        hotel_room_id: 'ROOM-1', room_number: '101', room_label: '101', floor: '1', room_status: 'available',
      }],
    } as unknown as CheckInDetailDto;
  }

  it('muestra el banner accionable con el faltante cuando el check-in responde 409 deposit_not_met', async () => {
    const { fixture, component, checkInApi } = await renderDetail(checkinableDetail());

    (checkInApi.completeCheckInWithDetail as jest.Mock).mockReturnValue(
      throwError(() => ({
        status: 409,
        message: 'Esta propiedad exige un depósito mínimo del 30% ($75.00) para el check-in.',
        details: {
          detail: {
            code: 'deposit_not_met',
            message: 'Esta propiedad exige un depósito mínimo del 30% ($75.00) para el check-in.',
            deposit_percent: 30,
            min_deposit: 75,
            paid_total: 50,
            missing: 25,
          },
        },
      })),
    );

    component.keysDelivered.set(true);
    component.goToStep(5);
    component.completeCheckIn();
    await Promise.resolve();
    fixture.detectChanges();

    expect(component.depositGate()).toEqual({
      percent: 30,
      minDeposit: 75,
      paid: 50,
      missing: 25,
      message: 'Esta propiedad exige un depósito mínimo del 30% ($75.00) para el check-in.',
    });

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Depósito mínimo no cubierto');
    expect(text).toContain('75.00');
    expect(text).toContain('25.00');
    expect(text).toContain('Registrar cobro en Facturación');
    expect(fixture.nativeElement.querySelector('.ciw-deposit-banner')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('a.ciw-deposit-banner-link')).not.toBeNull();
  });

  it('sigue usando el toast de error genérico cuando el 409 no es del gate de depósito', async () => {
    const { fixture, component, checkInApi } = await renderDetail(checkinableDetail());

    (checkInApi.completeCheckInWithDetail as jest.Mock).mockReturnValue(
      throwError(() => ({
        status: 409,
        message: 'El turno activo superó el límite de horas sin cerrarse.',
      })),
    );

    component.keysDelivered.set(true);
    component.goToStep(5);
    component.completeCheckIn();
    await Promise.resolve();
    fixture.detectChanges();

    expect(component.depositGate()).toBeNull();
    expect(component.completeError()).toContain('turno activo');
    expect(fixture.nativeElement.querySelector('.ciw-deposit-banner')).toBeNull();
  });
});
