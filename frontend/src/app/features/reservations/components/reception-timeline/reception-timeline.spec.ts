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
