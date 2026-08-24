import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ReservationsAuthService } from '../../services/reservations-auth.service';
import { ReservationsListPageComponent } from './reservations-list-page';

describe('ReservationsListPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
      currentUser: () => null,
    } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('deshabilita la exportación sin reports.download', () => {
    const ctx = setup(false);
    expect(ctx.component.canExport()).toBe(false);
  });

  it('habilita la exportación con reports.download', () => {
    const ctx = setup(true);
    expect(ctx.component.canExport()).toBe(true);
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});

describe('ReservationsListPageComponent (confirmación masiva de pendientes)', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      hasPermission: jest.fn(() => true),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
      currentUser: () => null,
    } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
        {
          provide: ConfirmDialogService,
          useValue: { open: jest.fn().mockResolvedValue(true) },
        },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance };
  }

  const pending = (bookingId: string) => ({ bookingId, status: 'pending', guestName: 'G' } as never);
  const confirmed = (bookingId: string) => ({ bookingId, status: 'confirmed', guestName: 'G' } as never);

  it('canBulkConfirm es false sin selección', () => {
    const { component } = setup();
    expect(component.canBulkConfirm()).toBe(false);
  });

  it('canBulkConfirm es true cuando todas las seleccionadas están pendientes', () => {
    const { component } = setup();
    component.selectedRows.set([pending('A'), pending('B')]);
    expect(component.canBulkConfirm()).toBe(true);
  });

  it('canBulkConfirm es false si la selección mezcla pendientes con confirmadas', () => {
    const { component } = setup();
    component.selectedRows.set([pending('A'), confirmed('B')]);
    expect(component.canBulkConfirm()).toBe(false);
  });

  it('hasPendingSelected / hasConfirmedSelected reflejan la composición de la selección', () => {
    const { component } = setup();
    expect(component.hasPendingSelected()).toBe(false);
    component.selectedRows.set([confirmed('A')]);
    expect(component.hasPendingSelected()).toBe(false);
    expect(component.hasConfirmedSelected()).toBe(true);
    component.selectedRows.set([pending('A'), confirmed('B')]);
    expect(component.hasPendingSelected()).toBe(true);
    expect(component.hasConfirmedSelected()).toBe(true);
  });

  it('canBulkConfirm se desactiva si una pendiente seleccionada es no-show', () => {
    const { component } = setup();
    component.selectedRows.set([{ bookingId: 'A', status: 'pending', stayStatus: 'no_show', guestName: 'G' } as never]);
    expect(component.canBulkConfirm()).toBe(false);
  });

  it('canBulkCheckIn se desactiva si una confirmada seleccionada es no-show', () => {
    const { component } = setup();
    component.selectedRows.set([{ bookingId: 'A', status: 'confirmed', stayStatus: 'no_show', guestName: 'G' } as never]);
    expect(component.canBulkCheckIn()).toBe(false);
  });

  it('canBulkCheckIn se desactiva si una confirmada seleccionada ya hizo check-in', () => {
    const { component } = setup();
    component.selectedRows.set([{ bookingId: 'A', status: 'confirmed', stayStatus: 'checked_in', guestName: 'G' } as never]);
    expect(component.canBulkCheckIn()).toBe(false);
  });
});

describe('ReservationsListPageComponent (aviso post-masivo de checklist incompleto)', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      hasPermission: jest.fn(() => true),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
      currentUser: () => null,
    } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
        {
          provide: ConfirmDialogService,
          useValue: { open: jest.fn().mockResolvedValue(true) },
        },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance };
  }    const confirmed = (bookingId: string) => ({
    bookingId,
    status: 'confirmed',
    guestName: 'Horuz Test',
  } as never);

  it('marca las reservas cuyo checklist viene incompleto tras el check-in masivo', async () => {
    const { component } = setup();
    const http = TestBed.inject(HttpTestingController);
    component.selectedRows.set([confirmed('BK-A')]);

    const pending = component.onBulkCheckIn();
    // Deja que el diálogo mockeado resuelva y el loop llegue al POST.
    await new Promise((r) => setTimeout(r, 0));
    const req = http.expectOne('/api/management/check-ins/BK-A/complete');
    req.flush({
      booking_id: 'BK-A',
      stay_status: 'checked_in',
      checklist: { complete: false },
    });
    await pending;

    expect(component.incompleteChecklistRows()).toEqual([
      { bookingId: 'BK-A', guestName: 'Horuz Test' },
    ]);
  });

  it('no marca reservas con checklist completo', async () => {
    const { component } = setup();
    const http = TestBed.inject(HttpTestingController);
    component.selectedRows.set([confirmed('BK-B')]);

    const pending = component.onBulkCheckIn();
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/management/check-ins/BK-B/complete').flush({
      booking_id: 'BK-B',
      checklist: { complete: true },
    });
    await pending;

    expect(component.incompleteChecklistRows()).toEqual([]);
  });

  it('descarta el aviso sin recargar', () => {
    const { component } = setup();
    component.incompleteChecklistRows.set([{ bookingId: 'BK-A', guestName: 'Horuz Test' }]);
    component.dismissIncompleteChecklist();
    expect(component.incompleteChecklistRows()).toEqual([]);
  });

  it('reporta el check-in masivo con TODO fallido en UN toast global de error (sin verde engañoso)', async () => {
    const { component } = setup();
    const http = TestBed.inject(HttpTestingController);
    const toast = TestBed.inject(ToastService);
    component.selectedRows.set([confirmed('BK-C')]);

    const pending = component.onBulkCheckIn();
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/management/check-ins/BK-C/complete').flush(
      { detail: 'No hay un turno de caja activo para esta propiedad.' },
      { status: 409, statusText: 'Conflict' },
    );
    await pending;

    const msgs = toast.toasts();
    // Todo falló → un solo toast de error con el conteo; nada de success/warning
    // que repitan lo que el error ya dice.
    expect(
      msgs.some((t) => t.type === 'error' && t.message.includes('Check-in masivo no completado · 1 reserva')),
    ).toBe(true);
    expect(msgs.some((t) => t.type === 'success')).toBe(false);
    expect(msgs.some((t) => t.type === 'warning')).toBe(false);
  });

  it('reporta el check-in masivo con éxito parcial en DOS toasts globales (success + warning)', async () => {
    const { component } = setup();
    const http = TestBed.inject(HttpTestingController);
    const toast = TestBed.inject(ToastService);
    component.selectedRows.set([confirmed('BK-C1'), confirmed('BK-C2')]);

    const pending = component.onBulkCheckIn();
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/management/check-ins/BK-C1/complete').flush({
      booking_id: 'BK-C1',
      checklist: { complete: true },
    });
    // El loop es secuencial: tras resolver la primera fila, esperá un tick
    // para que el segundo POST llegue al HttpTestingController.
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/management/check-ins/BK-C2/complete').flush(
      { detail: 'El turno activo lleva más de 12 horas sin cerrarse.' },
      { status: 409, statusText: 'Conflict' },
    );
    await pending;

    const msgs = toast.toasts();
    // Éxito parcial: el success informa cuántas OK y el warning cuáles fallaron.
    expect(msgs.some((t) => t.type === 'success' && t.message.includes('1 ok, 1 con error'))).toBe(true);
    expect(msgs.some((t) => t.type === 'warning' && t.message.includes('Fallaron 1 de 2'))).toBe(true);
    expect(msgs.some((t) => t.type === 'error')).toBe(false);
  });

  it('reporta el éxito total del check-in masivo en un toast global de éxito', async () => {
    const { component } = setup();
    const http = TestBed.inject(HttpTestingController);
    const toast = TestBed.inject(ToastService);
    component.selectedRows.set([confirmed('BK-D')]);

    const pending = component.onBulkCheckIn();
    await new Promise((r) => setTimeout(r, 0));
    http.expectOne('/api/management/check-ins/BK-D/complete').flush({
      booking_id: 'BK-D',
      checklist: { complete: true },
    });
    await pending;

    expect(
      toast.toasts().some((t) => t.type === 'success' && t.message.includes('Check-in masivo completado · 1 reserva')),
    ).toBe(true);
  });
});

describe('ReservationsListPageComponent (estadías pasadas del huésped — solo lectura)', () => {
  const PAST_STAYS_PAYLOAD = {
    items: [
      {
        booking_id: 'BK-PAST-NS',
        prop_id: 1,
        hotel_label: 'Hotel Lima Centro',
        guest_name: 'Horuz',
        check_in_date: '2026-08-01',
        check_out_date: '2026-08-03',
        total_price: 150,
        currency: 'USD',
        status: 'confirmed',
        stay_status: 'no_show',
        read_only_reason: 'no_show',
        no_show_penalty_amount: 75,
      },
      {
        booking_id: 'BK-PAST-OUT',
        prop_id: 1,
        hotel_label: 'Hotel Lima Centro',
        guest_name: 'Horuz',
        check_in_date: '2026-07-10',
        check_out_date: '2026-07-13',
        total_price: 300,
        currency: 'USD',
        status: 'checked_out',
        stay_status: 'checked_out',
        read_only_reason: 'dates_passed',
        no_show_penalty_amount: null,
      },
    ],
  };

  function setupClient() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = { hasPermission: jest.fn(() => true), currentUser: () => null } as unknown as AuthService;
    const propertyContext = {
      currentPropId: signal(0),
      currentPropLabel: signal(''),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AuthService, useValue: auth },
        { provide: ConfirmDialogService, useValue: { open: jest.fn().mockResolvedValue(true) } },
        {
          provide: ReservationsAuthService,
          useValue: { isStaff: signal(false), isClient: signal(true) },
        },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      el: fixture.nativeElement as HTMLElement,
      http: TestBed.inject(HttpTestingController),
    };
  }

  function flushPastStays(ctx: ReturnType<typeof setupClient>) {
    const req = ctx.http.expectOne((r) => r.url.includes('/reservations/past-stays'));
    req.flush(PAST_STAYS_PAYLOAD);
    return req;
  }

  /** El httpResource aplica la respuesta en un microtask: esperar el tick
   *  antes de re-renderizar (mismo patrón que los specs con rxResource). */
  const settle = async () => {
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
  };

  it('el cliente ve la zona de estadías pasadas con el motivo server-authoritative', async () => {
    const ctx = setupClient();
    flushPastStays(ctx);
    await settle();
    ctx.fixture.detectChanges();

    const zone = ctx.el.querySelector('.past-stays');
    expect(zone).not.toBeNull();
    const text = zone?.textContent ?? '';
    // No-show: badge + explicación.
    expect(text).toContain('No Show');
    expect(text).toContain('no se presentó');
    // Fechas pasadas: badge + explicación.
    expect(text).toContain('Finalizada');
    expect(text).toContain('fechas ya pasaron');
    // Ambas estadías listadas con su hotel.
    expect(text).toContain('BK-PAST-NS');
    expect(text).toContain('BK-PAST-OUT');
    expect(text).toContain('Hotel Lima Centro');
  });

  it('la zona es de SOLO LECTURA: ningún botón ni enlace dentro', async () => {
    const ctx = setupClient();
    flushPastStays(ctx);
    await settle();
    ctx.fixture.detectChanges();

    const zone = ctx.el.querySelector('.past-stays');
    expect(zone?.querySelectorAll('button').length).toBe(0);
    expect(zone?.querySelectorAll('a').length).toBe(0);
  });

  it('la tarjeta no-show muestra la penalización y el candado de solo lectura', async () => {
    const ctx = setupClient();
    flushPastStays(ctx);
    await settle();
    ctx.fixture.detectChanges();

    const card = Array.from(ctx.el.querySelectorAll('.past-stay-card'))
      .find((c) => c.textContent?.includes('BK-PAST-NS'));
    expect(card).toBeDefined();
    expect(card?.textContent).toContain('$75.00');
    expect(card?.querySelector('.past-stay-lock')).not.toBeNull();
    expect(card?.classList.contains('is-no-show')).toBe(true);
  });

  it('sin estadías pasadas la zona no se renderiza', async () => {
    const ctx = setupClient();
    const req = ctx.http.expectOne((r) => r.url.includes('/reservations/past-stays'));
    req.flush({ items: [] });
    await settle();
    ctx.fixture.detectChanges();

    expect(ctx.el.querySelector('.past-stays')).toBeNull();
  });
});

describe('ReservationsListPageComponent (staff no ve estadías pasadas)', () => {
  function setupStaff() {
    TestBed.configureTestingModule({
      imports: [ReservationsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: Router,
          useValue: {
            events: new Subject<unknown>().asObservable(),
            navigate: jest.fn(),
            routerState: { snapshot: { root: { data: {}, firstChild: null } } },
          } as unknown as Router,
        },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({}) },
            queryParamMap: of(convertToParamMap({})),
          },
        },
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(0),
            currentPropLabel: signal(''),
            mode: signal('all'),
            ready: signal(true),
            assignedProperties: signal([]),
            defaultPropId: signal(0),
            singleHotelMode: signal(false),
            setProperty: jest.fn(),
            clear: jest.fn(),
          } as unknown as PropertyContextService,
        },
        { provide: AuthService, useValue: { hasPermission: jest.fn(() => true), currentUser: () => null } },
        { provide: ConfirmDialogService, useValue: { open: jest.fn().mockResolvedValue(true) } },
        {
          provide: ReservationsAuthService,
          useValue: { isStaff: signal(true), isClient: signal(false) },
        },
      ],
    });

    const fixture = TestBed.createComponent(ReservationsListPageComponent);
    fixture.detectChanges();
    return { fixture, el: fixture.nativeElement as HTMLElement, http: TestBed.inject(HttpTestingController) };
  }

  it('ni pide el endpoint ni renderiza la zona para staff', () => {
    const ctx = setupStaff();

    const pastReqs = ctx.http.match((r) => r.url.includes('/reservations/past-stays'));
    expect(pastReqs.length).toBe(0);
    expect(ctx.el.querySelector('.past-stays')).toBeNull();
  });
});
