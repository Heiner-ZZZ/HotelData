import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { NoShowService, type NoShowResult } from '../../../../shared/services/no-show.service';
import type { CheckOutDetailDto } from '../../services/check-outs-api.service';
import { CheckOutDetailPageComponent } from './check-out-detail-page';

describe('CheckOutDetailPageComponent', () => {
  const COMPLETED_DETAIL: CheckOutDetailDto = {
    booking_id: 'BK-1',
    prop_id: 1,
    hotel_label: 'Hotel Lima Centro',
    folio: null,
    guest_name: 'Guest Prueba',
    guest_email: 'guest@test.com',
    guest_phone: '',
    cedula: '',
    check_in_date: '2026-08-09',
    check_in_date_actual: null,
    check_in_time_actual: null,
    check_in_by: null,
    check_out_date: '2026-08-11',
    total_price: 218,
    currency: 'USD',
    total_nights: 2,
    rooms: 1,
    room_type_name: 'Habitación Standard',
    assigned_rooms: [],
    status: 'confirmed',
    stay_status: 'checked_out',
    payment_method: '',
    booking_source: 'web',
    total_charges: 0,
    deposit_received: false,
    payment_pending: false,
    invoice: null,
    charges: [],
    charges_total: 0,
    charges_by_category: {},
    category_totals: {},
    check_out_room_inspected: true,
    check_out_keys_returned: true,
    check_out_damages_found: false,
    check_out_late_checkout_fee: 0,
    check_out_discount: 0,
    check_out_discount_reason: '',
    check_out_payment_method: '',
    check_out_payment_ref: '',
    check_out_observations: '',
    check_out_date_actual: '2026-08-11',
    check_out_time_actual: '12:04',
    check_out_by: 'recep.prueba',
    late_checkout_context: null,
    check_out_mode: null,
    late_checkout_fee: 0,
    late_checkout_minutes: 0,
    late_checkout_approved_by: null,
    late_checkout_reason: '',
    late_checkout_policy_time: null,
    check_out_shift_id: 'shift-1',
    check_out_shift: {
      shift_type: 'morning',
      shift_label: 'Matutino (08:00-16:00)',
      employee: 'Carlos Pérez',
      opened_by: 'recep.prueba',
      start_time: '2026-08-11T08:00:00+00:00',
    },
  };

  async function renderDetail(dto: CheckOutDetailDto, opts?: { hasPermission?: boolean }) {
    await TestBed.configureTestingModule({
      imports: [CheckOutDetailPageComponent],
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
        { provide: AuthService, useValue: { hasPermission: jest.fn(() => opts?.hasPermission ?? true) } },
        { provide: NoShowService, useValue: { markNoShowWithConfirm: jest.fn(), successMessage: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(CheckOutDetailPageComponent);
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-outs/BK-1/detail'));
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
      imports: [CheckOutDetailPageComponent],
      providers: [
        // Interceptor real → el 403 llega como ApiError plano (camino vivo),
        // no como HttpErrorResponse.
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

    const fixture = TestBed.createComponent(CheckOutDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-outs/BK-1/detail'));
    req.flush({ detail: 'Permiso requerido: check-outs.read' }, { status: 403, statusText: 'Forbidden' });

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
    expect(() => component.roomTotal()).not.toThrow();
    expect(() => component.chargesTotal()).not.toThrow();
    expect(() => component.grandTotal()).not.toThrow();
    expect(consoleSpy).not.toHaveBeenCalled();
  });

  it('la vista completada muestra el turno y el empleado responsable del check-out', async () => {
    const { fixture } = await renderDetail(COMPLETED_DETAIL);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Turno');
    expect(text).toContain('Carlos Pérez');
    expect(text).toContain('Matutino');
  });

  it('sin turno estampado no muestra fila de turno', async () => {
    const { fixture } = await renderDetail({ ...COMPLETED_DETAIL, check_out_shift_id: null, check_out_shift: null });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Carlos Pérez');
  });

  // ═══ Reserva sin check-in: no se puede liquidar ═══
  const NEVER_CHECKED_IN: CheckOutDetailDto = {
    ...COMPLETED_DETAIL,
    // Reserva confirmada que NUNCA registró check-in (stay_status ausente),
    // pero con habitación asignada — el caso que antes habilitaba el wizard.
    stay_status: '',
    assigned_rooms: [
      { hotel_room_id: 'HR-1-101', room_number: '101', room_label: '101', floor: '2', room_status: 'vacant_clean' },
    ],
    check_out_date_actual: null,
    check_out_time_actual: null,
    check_out_by: null,
    check_out_shift_id: null,
    check_out_shift: null,
  };

  it('bloquea el check-out de una reserva que nunca tuvo check-in', async () => {
    const { fixture, component } = await renderDetail(NEVER_CHECKED_IN);
    expect(component.canComplete()).toBe(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text.toLowerCase()).toContain('sin check-in');
    // El wizard no se renderiza: no hay botón Continuar ni pasos.
    expect(text).not.toContain('Continuar');
  });

  it('muestra el estado no-show en el header para reservas marcadas no_show', async () => {
    const { fixture, component } = await renderDetail({ ...NEVER_CHECKED_IN, stay_status: 'no_show' });
    expect(component.canComplete()).toBe(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('No-show');
    expect(text).not.toContain('Continuar');
  });

  it('una estancia con check-in activo sigue pudiendo liquidarse', async () => {
    const { fixture, component } = await renderDetail({ ...NEVER_CHECKED_IN, stay_status: 'checked_in' });
    expect(component.canComplete()).toBe(true);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('sin check-in');
  });

  // ═══ Cierre manual: Marcar no-show desde el detalle de check-out ═══
  function localDateStr(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function pastNeverCheckedIn(): CheckOutDetailDto {
    const past = new Date();
    past.setDate(past.getDate() - 2);
    const pastStr = localDateStr(past);
    return { ...NEVER_CHECKED_IN, stay_status: '', check_in_date: pastStr, check_out_date: pastStr };
  }

  function findNoShowButton(fixture: { nativeElement: HTMLElement }): HTMLButtonElement | undefined {
    return Array.from(fixture.nativeElement.querySelectorAll('button')).find(
      (b) => (b.textContent ?? '').includes('Marcar no-show'),
    );
  }

  it('muestra el botón Marcar no-show en el panel bloqueado (estadía terminada, sin check-in)', async () => {
    const { fixture, component } = await renderDetail(pastNeverCheckedIn());
    expect(component.canMarkNoShow()).toBe(true);
    expect(findNoShowButton(fixture)).toBeDefined();
  });

  it('NO muestra el botón cuando la reserva ya está marcada no_show', async () => {
    const { fixture, component } = await renderDetail({ ...pastNeverCheckedIn(), stay_status: 'no_show' });
    expect(component.canMarkNoShow()).toBe(false);
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('NO muestra el botón sin permiso reservations.update', async () => {
    const { fixture, component } = await renderDetail(pastNeverCheckedIn(), { hasPermission: false });
    expect(component.canMarkNoShow()).toBe(false);
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('NO muestra el botón si la estadía aún no terminó (check-out futuro)', async () => {
    const future = new Date();
    future.setDate(future.getDate() + 2);
    const today = new Date();
    const { fixture, component } = await renderDetail({
      ...NEVER_CHECKED_IN,
      stay_status: '',
      check_in_date: localDateStr(today),
      check_out_date: localDateStr(future),
    });
    expect(component.canMarkNoShow()).toBe(false);
    expect(findNoShowButton(fixture)).toBeUndefined();
  });

  it('reconstruye el folio de no-show y su enlace después de recargar la página', async () => {
    const persisted = {
      ...pastNeverCheckedIn(),
      stay_status: 'no_show',
      folio: 'FL-NS-PERSISTED',
      no_show_penalty_amount: 94,
    } as CheckOutDetailDto;
    const { fixture, component } = await renderDetail(persisted);

    expect(component.noShowResult()).toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('FL-NS-PERSISTED');
    expect(text).toContain('Ver folio en Facturación');
  });

  it('marca no-show tras confirmar: llama al NoShowService compartido, muestra folio + enlace a Facturación', async () => {
    const RESULT: NoShowResult = {
      ok: true, booking_id: 'BK-1', penalty_amount: 94, check_in_date: '2026-08-01', folio_number: 'FL-NS-BK-20260',
    };
    const { fixture, component } = await renderDetail(pastNeverCheckedIn());
    const noShow = TestBed.inject(NoShowService);
    (noShow.markNoShowWithConfirm as jest.Mock).mockResolvedValue(RESULT);
    (noShow.successMessage as jest.Mock).mockImplementation(
      (r: NoShowResult) => `No-show registrado. Se cobró $${r.penalty_amount.toFixed(2)} como penalización.`,
    );

    findNoShowButton(fixture)!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(noShow.markNoShowWithConfirm).toHaveBeenCalledWith('BK-1', 'Guest Prueba');
    expect(component.noShowResult()).toEqual({ folio_number: 'FL-NS-BK-20260', penalty_amount: 94 });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('FL-NS-BK-20260');
    expect(text).toContain('Ver folio en Facturación');
  });

  it('no llama al servicio si el usuario cancela la confirmación', async () => {
    const { fixture, component } = await renderDetail(pastNeverCheckedIn());
    const noShow = TestBed.inject(NoShowService);
    (noShow.markNoShowWithConfirm as jest.Mock).mockResolvedValue(null);

    component.markNoShow();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.noShowResult()).toBeNull();
    expect(component.successMessage()).toBe('');
  });

  // ═══ Late check-out: ventana gobernada por la política ═══
  function lateCtx(overrides: Partial<NonNullable<CheckOutDetailDto['late_checkout_context']>> = {}) {
    return {
      enabled: true,
      is_late: true,
      minutes_after: 120,
      courtesy_minutes: 60,
      requires_approval: true,
      check_out_time: '12:00',
      default_fee: 20,
      real_time: '14:30',
      ...overrides,
    };
  }

  const CHECKED_IN_DETAIL: CheckOutDetailDto = {
    ...COMPLETED_DETAIL,
    stay_status: 'checked_in',
    check_out_date_actual: null,
    check_out_time_actual: null,
    check_out_by: null,
    check_out_shift_id: null,
    check_out_shift: null,
    assigned_rooms: [
      { hotel_room_id: 'HR-1-101', room_number: '101', room_label: '101', floor: '2', room_status: 'occupied_clean' },
    ],
    late_checkout_context: null,
    check_out_mode: null,
    late_checkout_fee: 0,
    late_checkout_minutes: 0,
    late_checkout_approved_by: null,
    late_checkout_reason: '',
    late_checkout_policy_time: null,
  };

  it('dentro de la cortesía muestra el panel late sin cargo y fija late_courtesy', async () => {
    const { fixture, component } = await renderDetail({
      ...CHECKED_IN_DETAIL,
      late_checkout_context: lateCtx({ is_late: true, requires_approval: false, minutes_after: 30, default_fee: 0 }),
    });
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.lateMode()).toBe('late_courtesy');
    expect(component.lateCheckoutFee()).toBe(0);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Dentro de la cortesía');
    expect(text).toContain('sin cargo');
  });

  it('el panel late muestra la hora real de salida extendida (campo legible para recepción)', async () => {
    const { fixture, component } = await renderDetail({
      ...CHECKED_IN_DETAIL,
      late_checkout_context: lateCtx({ is_late: true, requires_approval: false, minutes_after: 30, real_time: '12:30' }),
    });
    component.currentStep.set(3);
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Salida real:');
    expect(text).toContain('12:30 hrs');
    expect(text).toContain('hora actual del hotel');
  });

  it('la vista de check-out completado muestra la salida extendida legible (modo, minutos y política)', async () => {
    const { fixture } = await renderDetail({
      ...COMPLETED_DETAIL,
      check_out_mode: 'late_approved',
      late_checkout_minutes: 150,
      late_checkout_policy_time: '12:00',
    });
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Hora salida');
    expect(text).toContain('12:04 hrs');
    expect(text).toContain('Salida extendida');
    expect(text).toContain('Aprobado');
    expect(text).toContain('150 min tras las 12:00');
  });

  it('sin ventana late no muestra el panel', async () => {
    const { fixture, component } = await renderDetail({
      ...CHECKED_IN_DETAIL,
      late_checkout_context: lateCtx({ is_late: false }),
    });
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.lateRequiresApproval()).toBe(false);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Late check-out');
  });

  it('fuera de la cortesía sin permiso bloquea el cierre con mensaje claro', async () => {
    const { fixture, component } = await renderDetail(
      { ...CHECKED_IN_DETAIL, late_checkout_context: lateCtx({}) },
      { hasPermission: false },
    );
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.lateBlocked()).toBe(true);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('aprobación del gerente');
    expect(text).toContain('check-ins.late_checkout_approve');
    // Texto accesible: el bloqueo se anuncia como alert (role=alert + aria-live).
    const alertEl = fixture.nativeElement.querySelector('.co-late-alert');
    expect(alertEl).not.toBeNull();
    expect(alertEl!.getAttribute('role')).toBe('alert');
    expect(alertEl!.getAttribute('aria-live')).toBe('polite');

    component.completeCheckOut();
    expect(component.completing()).toBe(false);
    expect(component.completeError()).toContain('aprobación del gerente');
    // Criterio de mensaje con acción: dice QUÉ hacer (derivar a gerencia),
    // no solo que el estado está bloqueado.
    expect(component.completeError()).toContain('Derivalo a gerencia');
    expect(component.completeError()).toContain('autorizar la salida extendida');
  });

  it('el gerente aprueba con motivo y cargo: envía late_approved y aplica el fee de la respuesta', async () => {
    const { fixture, component, httpTesting } = await renderDetail({
      ...CHECKED_IN_DETAIL,
      late_checkout_context: lateCtx({}),
    });
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.lateRequiresApproval()).toBe(true);
    // Default de la política como fee sugerido.
    expect(component.lateCheckoutFee()).toBe(20);

    component.lateMode.set('late_approved');
    component.lateReason.set('Huésped espera vuelo de tarde');
    component.lateCheckoutFee.set(25);
    component.completeCheckOut();

    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-outs/BK-1/complete'));
    expect(req.request.body).toMatchObject({
      late_checkout_mode: 'late_approved',
      late_checkout_approved: true,
      late_checkout_reason: 'Huésped espera vuelo de tarde',
      late_checkout_fee: 25,
    });
    req.flush({
      booking_id: 'BK-1',
      stay_status: 'checked_out',
      check_out_mode: 'late_approved',
      late_checkout_fee: 25,
    });
    await fixture.whenStable();
    fixture.detectChanges();

    // El next del flujo corrió: sale del modo completing y avanza al paso 5.
    expect(component.completing()).toBe(false);
    expect(component.currentStep()).toBe(5);
    expect(component.lateCheckoutFee()).toBe(25);
  });

  // ═══ Liquidación: TOTAL/SALDO = suma del breakdown + reconciliación ═══
  function invoiceFixture(
    overrides: Partial<NonNullable<CheckOutDetailDto['invoice']>> = {},
  ): NonNullable<CheckOutDetailDto['invoice']> {
    return {
      id: 'inv-1',
      invoice_number: 'INV-001',
      subtotal: 200,
      room_subtotal: 200,
      extras_total: 0,
      taxes: 32,
      total: 232,
      status: 'issued',
      issued_at: '2026-08-10T10:00:00',
      paid_at: null,
      notes: null,
      line_items: [],
      ...overrides,
    };
  }

  /** Estancia checked_in con factura emitida ANTES de los cargos: alojamiento
   *  200 (facturado) + 50 de extras registrados después (sin facturar). */
  function checkedInLiquidation(overrides: Partial<CheckOutDetailDto> = {}): CheckOutDetailDto {
    const charge = {
      concept: 'Cena', amount: 50, quantity: 1, total: 50,
      category: 'restaurante', note: '', created_at: '2026-08-10T18:00:00',
    };
    return {
      ...CHECKED_IN_DETAIL,
      total_price: 200,
      charges_total: 50,
      charges: [charge],
      charges_by_category: { restaurante: [charge] },
      category_totals: { restaurante: 50 },
      invoice: invoiceFixture(),
      ...overrides,
    };
  }

  it('TOTAL es la suma del breakdown mostrado aunque la factura no incluya los cargos nuevos', async () => {
    const { fixture, component } = await renderDetail(checkedInLiquidation());
    component.currentStep.set(3);
    fixture.detectChanges();

    // breakdown: 200 alojamiento + 50 extras + 0 late − 0 descuento = 250; IVA 16% = 40.
    expect(component.subtotal()).toBe(250);
    expect(component.taxes()).toBe(40);
    expect(component.grandTotal()).toBe(290);
    // Sin depósito ni factura pagada → SALDO = TOTAL.
    expect(component.balanceDue()).toBe(290);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('$290.00');
  });

  it('SALDO = TOTAL − Pagado cuando la factura está pagada (queda cancelado)', async () => {
    const { fixture, component } = await renderDetail(
      checkedInLiquidation({ invoice: invoiceFixture({ status: 'paid', paid_at: '2026-08-10T12:00:00' }) }),
    );
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.hasExistingPayments()).toBe(true);
    expect(component.totalPaid()).toBe(component.grandTotal());
    expect(component.balanceDue()).toBe(0);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('$0.00');
  });

  it('muestra la nota de reconciliación cuando la factura no cubre los cargos adicionales', async () => {
    const { fixture, component } = await renderDetail(checkedInLiquidation());
    component.currentStep.set(3);
    fixture.detectChanges();

    // subtotal vivo 250 − factura 200 = 50 sin facturar.
    expect(component.invoiceReconcileNote()).toEqual({ invoice_number: 'INV-001', gap: 50 });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('no cubre los cargos adicionales');
    expect(text).toContain('INV-001');
    expect(text).toContain('$50.00');
    // Nota accesible: role=note + aria-live para anunciarla.
    const noteEl = fixture.nativeElement.querySelector('.co-liq-reconcile');
    expect(noteEl).not.toBeNull();
    expect(noteEl!.getAttribute('role')).toBe('note');
    expect(noteEl!.getAttribute('aria-live')).toBe('polite');
  });

  it('no muestra la nota cuando la factura cubre el breakdown y usa sus impuestos', async () => {
    const { fixture, component } = await renderDetail(
      checkedInLiquidation({ invoice: invoiceFixture({ subtotal: 250 }) }),
    );
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.invoiceCoversBreakdown()).toBe(true);
    expect(component.invoiceReconcileNote()).toBeNull();
    // Sin ajustes y cubierta: se conservan los impuestos fiscales de la factura.
    expect(component.taxes()).toBe(32);
    expect(component.grandTotal()).toBe(282);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('no cubre los cargos adicionales');
  });

  /** Estancia ya liquidada (check-out completado) con factura corta: la vista
   *  final del folio también debe advertir los cargos sin facturar. */
  function checkedOutLiquidation(overrides: Partial<CheckOutDetailDto> = {}): CheckOutDetailDto {
    const charge = {
      concept: 'Cena', amount: 50, quantity: 1, total: 50,
      category: 'restaurante', note: '', created_at: '2026-08-10T18:00:00',
    };
    return {
      ...COMPLETED_DETAIL,
      total_price: 200,
      charges_total: 50,
      charges: [charge],
      charges_by_category: { restaurante: [charge] },
      category_totals: { restaurante: 50 },
      invoice: invoiceFixture(),
      ...overrides,
    };
  }

  it('la vista de check-out completado advierte cargos sin facturar (nota de reconciliación)', async () => {
    const { fixture, component } = await renderDetail(checkedOutLiquidation());
    fixture.detectChanges();

    // checkoutDone → folio final renderizado; subtotal 250 − factura 200 = 50.
    expect(component.checkoutDone()).toBe(true);
    expect(component.invoiceReconcileNote()).toEqual({ invoice_number: 'INV-001', gap: 50 });
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Check-out completado');
    expect(text).toContain('no cubre los cargos adicionales');
    expect(text).toContain('INV-001');
    expect(text).toContain('$50.00');
    const noteEl = fixture.nativeElement.querySelector('.co-liq-reconcile');
    expect(noteEl).not.toBeNull();
    expect(noteEl!.getAttribute('role')).toBe('note');
    expect(noteEl!.getAttribute('aria-live')).toBe('polite');
    const invoiceRow = fixture.nativeElement.querySelector('.co-liq-reconcile-invoice');
    expect(invoiceRow).not.toBeNull();
    expect(invoiceRow!.getAttribute('aria-label')).toBe('Datos de la factura');
    expect(invoiceRow!.textContent).toContain('INV-001');
    expect(invoiceRow!.textContent).toContain('Estado: Emitida');
    expect(invoiceRow!.textContent).toContain('Emitida: 10/08/2026 10:00');
  });

  it('la vista completada no muestra la nota cuando la factura cubre el breakdown', async () => {
    const { fixture, component } = await renderDetail(
      checkedOutLiquidation({ invoice: invoiceFixture({ subtotal: 250 }) }),
    );
    fixture.detectChanges();

    expect(component.invoiceReconcileNote()).toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Check-out completado');
    expect(text).not.toContain('no cubre los cargos adicionales');
  });

  // ═══ Re-facturación: factura corta → complementaria por el gap ═══

  it('el paso 4 muestra la acción de re-facturación cuando la factura quedó corta', async () => {
    const { fixture, component } = await renderDetail(checkedInLiquidation());
    component.currentStep.set(4);
    fixture.detectChanges();

    // gap = subtotal vivo 250 − factura 200 = 50 → botón visible con el monto.
    expect(component.invoiceReconcileNote()).toEqual({ invoice_number: 'INV-001', gap: 50 });
    const btn = fixture.nativeElement.querySelector('.co-inv-complement');
    expect(btn).not.toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Re-facturar gap');
    expect(text).toContain('Complementaria por $50.00');
  });

  it('oculta la acción de re-facturación cuando no hay gap (factura cubre el breakdown)', async () => {
    const { fixture, component } = await renderDetail(
      checkedInLiquidation({ invoice: invoiceFixture({ subtotal: 250 }) }),
    );
    component.currentStep.set(4);
    fixture.detectChanges();

    expect(component.invoiceReconcileNote()).toBeNull();
    expect(fixture.nativeElement.querySelector('.co-inv-complement')).toBeNull();
  });

  it('re-facturar emite la complementaria por el gap y despeja la nota al recargar', async () => {
    const { fixture, component, httpTesting } = await renderDetail(checkedInLiquidation());
    component.currentStep.set(4);
    fixture.detectChanges();

    const btn = fixture.nativeElement.querySelector('.co-inv-complement') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    btn.click();
    fixture.detectChanges();

    // POST /billing/invoices/complement → factura complementaria por el gap.
    const compReq = httpTesting.expectOne(
      (r) => r.method === 'POST' && r.url.includes('/billing/invoices/complement'),
    );
    expect(compReq.request.body).toEqual({ booking_id: 'BK-1', prop_id: 1 });
    compReq.flush({ id: 'inv-2', invoice_number: 'INV-COMP-001', status: 'issued', total: 58 });

    // httpResource.reload() dispara el fetch cuando el effect interno del
    // resource corre (detectChanges), no en el mismo microtask del flush.
    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    // El emit recarga el detalle: covered_subtotal ahora cubre el subtotal vivo.
    const reloadReq = httpTesting.expectOne(
      (r) => r.url.includes('/management/check-outs/BK-1/detail'),
    );
    reloadReq.flush(checkedInLiquidation({ invoice: invoiceFixture({ covered_subtotal: 250 }) }));

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    // La nota y el botón desaparecen; el mensaje de éxito confirma la emisión.
    expect(component.invoiceReconcileNote()).toBeNull();
    expect(fixture.nativeElement.querySelector('.co-inv-complement')).toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Factura complementaria INV-COMP-001 emitida');
  });

  it('SALDO descuenta el depósito del TOTAL (50% del alojamiento)', async () => {
    const { fixture, component } = await renderDetail(checkedInLiquidation({ deposit_received: true }));
    component.currentStep.set(3);
    fixture.detectChanges();

    expect(component.depositDeducted()).toBe(100);
    expect(component.totalPaid()).toBe(100);
    expect(component.balanceDue()).toBe(component.grandTotal() - 100);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('$190.00');
  });
});
