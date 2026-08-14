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
});
