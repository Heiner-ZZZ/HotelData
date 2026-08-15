import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { signal } from '@angular/core';
import { Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ThemeService } from '../../../../core/theme/theme.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ReceptionTimelineComponent } from './reception-timeline';

describe('ReceptionTimelineComponent', () => {
  it('lets the destination route metadata publish insert mode after physical-reservation navigation', async () => {
    const routerEvents = new Subject<unknown>();
    let resolveNavigation!: (success: boolean) => void;
    const navigate = jest.fn().mockImplementation(() => {
      const navigation = new Promise<boolean>((resolve) => {
        resolveNavigation = resolve;
      });
      // Angular emits NavigationStart after the click handler has returned.
      queueMicrotask(() => {
        routerEvents.next(new NavigationStart(1, '/management/recepcion/new'));
      });
      return navigation;
    });
    const router = {
      url: '/management/recepcion',
      events: routerEvents.asObservable(),
      navigate,
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    component.selectedSlot.set({
      roomId: 'room-101',
      roomNumber: '101',
      roomTypeId: 'suite',
      roomTypeName: 'Suite',
      startDate: '2026-08-05',
      endDate: '2026-08-06',
      checkInTime: '15:00',
      checkOutTime: '11:00',
    });

    const pendingNavigation = component.openPhysicalReservation();
    await Promise.resolve();
    expect(TestBed.inject(OperationModeService).mode()).toBe('read');

    (router as unknown as { url: string }).url = '/management/recepcion/new?prop_id=7';
    (router as unknown as { routerState: { snapshot: { root: { firstChild: unknown } } } }).routerState.snapshot.root.firstChild = {
      data: { operationMode: 'insert', operationDetail: 'Reserva' },
      firstChild: null,
    };
    routerEvents.next(new NavigationEnd(1, '/management/recepcion', '/management/recepcion/new'));
    resolveNavigation(true);
    await pendingNavigation;

    const mode = TestBed.inject(OperationModeService);
    expect(mode.mode()).toBe('insert');
    expect(mode.detail()).toBe('Reserva');
    expect(navigate).toHaveBeenCalledWith(
      ['/management/recepcion/new'],
      expect.objectContaining({ queryParams: expect.objectContaining({ prop_id: 7 }) }),
    );
  });

  it('does not publish insert when physical-reservation navigation is cancelled', async () => {
    const navigate = jest.fn().mockResolvedValue(false);
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate,
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    component.selectedSlot.set({
      roomId: 'room-101', roomNumber: '101', roomTypeId: 'suite', roomTypeName: 'Suite',
      startDate: '2026-08-05', endDate: '2026-08-06', checkInTime: '15:00', checkOutTime: '11:00',
    });

    await component.openPhysicalReservation();

    expect(TestBed.inject(OperationModeService).mode()).toBe('read');
  });

  it('does not publish insert when the router rejects the navigation', async () => {
    const navigate = jest.fn().mockRejectedValue(new Error('navigation failed'));
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate,
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    component.selectedSlot.set({
      roomId: 'room-101', roomNumber: '101', roomTypeId: 'suite', roomTypeName: 'Suite',
      startDate: '2026-08-05', endDate: '2026-08-06', checkInTime: '15:00', checkOutTime: '11:00',
    });

    await component.openPhysicalReservation();

    expect(TestBed.inject(OperationModeService).mode()).toBe('read');
  });

  it('defaults to the monthly timeline view at the start of the current month', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);

    expect(component.currentView()).toBe('TimelineMonth');
    const now = new Date();
    const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    expect(component.viewStartDate()).toBe(expected);
  });

  it('apila en la vista mensual los detalles y todos los iconos de la reserva', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    const appointment = document.createElement('div');
    appointment.className = 'e-appointment';

    component.onEventRendered({
      element: appointment,
      data: {
        VisualStatus: 'past',
        GuestName: 'Prueba Llegada Tarde',
        StatusLabel: 'Finalizada',
        Adults: 2,
        Children: 1,
        TotalNights: 2,
        LateCheckin: true,
      },
    } as never);

    expect(appointment.classList).toContain('timeline-appointment-stacked');
    expect(appointment.querySelector('.timeline-app-side')).toBeNull();
    expect(appointment.querySelector('.timeline-app-meta')?.parentElement).toBe(appointment);
    expect(appointment.querySelector('.timeline-late-marker')?.parentElement)
      .toBe(appointment.querySelector('.timeline-app-meta'));
    expect(appointment.querySelector('.timeline-app-meta-item .material-symbols-outlined')?.textContent)
      .toBe('group');
    expect(appointment.querySelectorAll('.timeline-app-meta-item .material-symbols-outlined')[1]?.textContent)
      .toBe('nights_stay');
    expect(appointment.querySelector('.timeline-late-marker .material-symbols-outlined')?.textContent)
      .toBe('schedule');
    fixture.destroy();
  });

  it('muestra personas, noches y llegada tarde en una estancia de una sola noche', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    const appointment = document.createElement('div');
    appointment.className = 'e-appointment';

    component.onEventRendered({
      element: appointment,
      data: {
        VisualStatus: 'active',
        GuestName: 'Prueba una noche',
        StatusLabel: 'Vigente',
        Adults: 2,
        Children: 1,
        TotalNights: 1,
        LateCheckin: true,
      },
    } as never);

    expect([...appointment.querySelectorAll(
      '.timeline-app-meta-item .material-symbols-outlined, .timeline-late-marker .material-symbols-outlined',
    )].map((icon) => icon.textContent)).toEqual(['group', 'nights_stay', 'schedule']);
    fixture.destroy();
  });

  it('mantiene visibles todos los iconos aunque la barra mensual sea estrecha', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance as unknown as {
      applyMetaDisclosure: (element: HTMLElement) => void;
    };
    fixture.componentRef.setInput('propId', 7);

    const appointment = document.createElement('div');
    appointment.className = 'e-appointment timeline-appointment-stacked';
    const meta = document.createElement('span');
    meta.className = 'timeline-app-meta';
    const people = document.createElement('span');
    people.className = 'timeline-app-meta-item';
    const nights = document.createElement('span');
    nights.className = 'timeline-app-meta-item';
    meta.append(people, nights);
    appointment.append(meta);
    document.body.append(appointment);

    jest.spyOn(appointment, 'getBoundingClientRect').mockReturnValue({ width: 100 } as DOMRect);
    component.applyMetaDisclosure(appointment);

    expect(meta.classList).not.toContain('timeline-app-meta--hidden');
    expect(people.classList).not.toContain('timeline-app-meta-item--hidden');
    expect(nights.classList).not.toContain('timeline-app-meta-item--hidden');
    appointment.remove();
    fixture.destroy();
  });

  it('asigna una altura mensual estable para separar reservas concurrentes en carriles', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    const appointment = document.createElement('div');
    appointment.className = 'e-appointment';

    component.onEventRendered({
      element: appointment,
      data: {
        Index: 1,
        VisualStatus: 'active',
        GuestName: 'Reserva concurrente',
        StatusLabel: 'Vigente',
        Adults: 2,
        Children: 0,
        TotalNights: 2,
        LateCheckin: false,
      },
    } as never);

    expect(appointment.classList).toContain('timeline-appointment-stacked');
    expect(appointment.style.getPropertyValue('height')).toBe('4.5rem');
    expect(appointment.style.getPropertyValue('min-height')).toBe('4.5rem');
    fixture.destroy();
  });

  it('keeps the timeline computable when housekeeping is forbidden (403)', async () => {
    const router = {
      url: '/management/recepcion',
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const theme = { isDark: signal(false) } as unknown as ThemeService;

    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: ThemeService, useValue: theme },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('propId', 7);
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    httpTesting
      .expectOne((req) => req.url.includes('/management/reception/calendar'))
      .flush({
        rooms: [],
        start_date: '2026-08-01',
        end_date: '2026-08-31',
        today: '2026-08-06',
        check_in_time: '15:00',
        check_out_time: '12:00',
      });
    httpTesting
      .expectOne((req) => req.url.includes('/housekeeping/room-status'))
      .flush({ detail: 'Permiso requerido: housekeeping.read' }, { status: 403, statusText: 'Forbidden' });

    // El error del httpResource aterriza en un microtask (promise interna);
    // esperar a que el estado 'error' se asiente antes de leer los computeds.
    await Promise.resolve();
    await Promise.resolve();
    expect(component.roomStatuses().size).toBe(0);
    expect(() => component.resources()).not.toThrow();
    httpTesting.verify();
  });
});

describe('ReceptionTimelineComponent — marcador de no-show en la barra', () => {
  async function createComponent() {
    const routerEvents = new Subject<unknown>();
    await TestBed.configureTestingModule({
      imports: [ReceptionTimelineComponent],
      providers: [
        provideHttpClient(),
        { provide: Router, useValue: { url: '/management/recepcion', events: routerEvents.asObservable(), navigate: jest.fn(), routerState: { snapshot: { root: { data: {}, firstChild: null } } } } },
        { provide: ThemeService, useValue: { isDark: signal(false) } },
        { provide: ToastService, useValue: { warning: jest.fn() } },
      ],
    }).compileComponents();
    const fixture = TestBed.createComponent(ReceptionTimelineComponent);
    return fixture.componentInstance;
  }

  function baseEvent(overrides: Record<string, unknown>) {
    return {
      StayStatus: 'no_show',
      ReopenWindow: 'open' as const,
      GuestName: 'Cliente Demo',
      LateCheckin: false,
      Adults: 1,
      Children: 0,
      TotalNights: 2,
      StatusLabel: 'Vigente',
      ...overrides,
    };
  }

  it('marca el no-show reabrible con el chip Reabrible y aria-label de ventana abierta', async () => {
    const component = await createComponent();
    const el = document.createElement('div');
    (component as unknown as { appendNoShowMarker: (e: HTMLElement, ev: unknown) => void })
      .appendNoShowMarker(el, baseEvent({ ReopenWindow: 'open' }));

    const marker = el.querySelector('.timeline-noshow-marker');
    expect(marker).not.toBeNull();
    // El chip "Reabrible" vive en el pseudo-elemento ::after del marcador
    // (no entra en textContent): la clase + aria-label fijan el contrato.
    expect(marker!.classList.contains('is-reopenable')).toBe(true);
    expect(marker!.getAttribute('aria-label')).toContain('reabrible');
    expect(marker!.querySelector('.material-symbols-outlined')?.textContent).toBe('event_busy');
  });

  it('no muestra el chip de reapertura en no-shows antiguos (ventana cerrada)', async () => {
    const component = await createComponent();
    const el = document.createElement('div');
    (component as unknown as { appendNoShowMarker: (e: HTMLElement, ev: unknown) => void })
      .appendNoShowMarker(el, baseEvent({ ReopenWindow: 'too_late' }));

    const marker = el.querySelector('.timeline-noshow-marker');
    expect(marker).not.toBeNull();
    expect(marker!.classList.contains('is-reopenable')).toBe(false);
    expect(marker!.getAttribute('aria-label')).toContain('cerrada');
  });

  it('no agrega marcador a reservas que no son no-show', async () => {
    const component = await createComponent();
    const el = document.createElement('div');
    (component as unknown as { appendNoShowMarker: (e: HTMLElement, ev: unknown) => void })
      .appendNoShowMarker(el, baseEvent({ StayStatus: 'checked_in', ReopenWindow: null }));

    expect(el.querySelector('.timeline-noshow-marker')).toBeNull();
  });
});
