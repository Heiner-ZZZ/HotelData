import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { RatesDashboardPageComponent } from './rates-dashboard-page';

// jsdom no implementa matchMedia; ThemeService (vía app-kpi-chart / page-header) lo necesita.
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }),
  });
}

/** El sub-nav global trae los accesos canónicos de Informes. */
const NAV_PAYLOAD = {
  items: [
    { slug: 'gestion.reservas.informes', parentSlug: 'gestion.reservas', position: 30, nodeType: 'container', label: 'Informes', href: null, icon: 'monitoring', visible: true, permissionCode: 'reports.tactical.read', horizontalMenu: true },
    { slug: 'gestion.reservas.informes.adr', parentSlug: 'gestion.reservas.informes', position: 10, nodeType: 'leaf', label: 'Dashboard ADR', href: '/management/rates/dashboard', icon: 'monitoring', visible: true, permissionCode: 'reports.rates.adr.read' },
    { slug: 'gestion.reservas.informes.calendario', parentSlug: 'gestion.reservas.informes', position: 20, nodeType: 'leaf', label: 'Calendario Tarifas', href: '/management/rates/calendar', icon: 'calendar_month', visible: true, permissionCode: 'reports.rates.calendar.read' },
    { slug: 'gestion.reservas.informes.solicitudes', parentSlug: 'gestion.reservas.informes', position: 30, nodeType: 'leaf', label: 'Dashboard Solicitudes', href: '/management/service-requests', icon: 'room_service', visible: true, permissionCode: 'reports.requests.read' },
  ],
};

function makeRow(overrides: Record<string, unknown> = {}) {
  return {
    date: '2026-08-20',
    prop_id: 1,
    hotel_label: 'Hotel Lima Centro',
    room_type_id: 'RT-1-DLX',
    room_type_label: 'Habitación Deluxe',
    currency: 'USD',
    booking_source: '',
    rooms_sold: 0,
    room_nights: 0,
    revenue: 0,
    cancelled_rooms: 0,
    available_rooms: 2,
    blocked_rooms: 0,
    total_rooms: 2,
    published_rate: null,
    rate_variance: 0,
    ...overrides,
  };
}

const DASHBOARD_DTO = () => ({
  available: true,
  source: 'clickhouse',
  date_from: '2026-07-26',
  date_to: '2026-08-24',
  prop_id: 1,
  summary: {
    adr: 150, revpar: 60, occupancy: 40, revenue: 300, room_nights: 2, rooms_sold: 2,
    cancelled_rooms: 0, capacity_nights: 5, range_days: 30, has_revenue: true, has_inventory: true,
    by_room_type: [], by_channel: [], by_hotel: [],
  },
  series: { labels: [], datasets: [] },
  rows: [
    // Una venta real y una fila de inventario sin revenue.
    makeRow({ revenue: 150, rooms_sold: 1, room_nights: 1 }),
    makeRow({ date: '2026-08-21', room_type_id: 'RT-1-STD', room_type_label: 'Habitación Standard' }),
  ],
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
  has_next: false,
  has_prev: false,
});

describe('RatesDashboardPageComponent', () => {
  let navigate: jest.Mock;

  beforeEach(async () => {
    navigate = jest.fn();

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });
    TestBed.overrideComponent(KpiChartComponent, {
      set: { template: '<span>kpi-stub</span>' },
    });

    await TestBed.configureTestingModule({
      imports: [RatesDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1' }) },
            queryParamMap: of(convertToParamMap({ prop_id: '1' })),
          },
        },
        {
          provide: Router,
          useValue: {
            events: new Subject<unknown>().asObservable(),
            navigate,
            routerState: { snapshot: { root: { data: {}, firstChild: null } } },
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
          },
        },
      ],
    }).compileComponents();
  });

  function setup(query: Record<string, string> = {}) {
    if (Object.keys(query).length) {
      const qp = convertToParamMap(query);
      const route = TestBed.inject(ActivatedRoute) as jasmine.SpyObj<ActivatedRoute>;
      (route as any).snapshot.queryParamMap = qp;
      (route as any).queryParamMap = of(qp);
    }
    const fixture = TestBed.createComponent(RatesDashboardPageComponent);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    const router = TestBed.inject(Router) as unknown as jest.Mocked<Router>;

    // El dashboard se pide al montar; el sub-nav global también.
    const reqs = http.match((r) => r.url.includes('/api/admin/navigation'));
    reqs.forEach((r) => r.flush(NAV_PAYLOAD));

    return {
      fixture,
      el: fixture.nativeElement as HTMLElement,
      http,
      router,
      flushDashboard: () => {
        const req = http.expectOne((r) => r.url.includes('/rates/analytics/room-performance'));
        req.flush(DASHBOARD_DTO());
        fixture.detectChanges();
        return req;
      },
    };
  }

  // ── Navegación ──

  it('NO renderiza el sub-nav local duplicado (.rpd-nav): la página ya tiene el sub-nav global', () => {
    const { el, flushDashboard } = setup();
    flushDashboard();

    expect(el.querySelector('nav.rpd-nav')).toBeNull();
    expect(el.querySelector('.rpd-nav-link')).toBeNull();
  });

  it('conserva el sub-nav global con los accesos de Informes', async () => {
    const { fixture, el, flushDashboard } = setup();
    flushDashboard();
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    fixture.detectChanges();

    const links = Array.from(el.querySelectorAll('.hrz-sub-nav .hrz-nav-label')).map((a) => a.textContent?.trim());
    expect(links).toContain('Dashboard ADR');
    expect(links).toContain('Calendario Tarifas');
  });

  // ── Filtro "solo con ganancias" ──

  it('propaga only_profitable=1 de la URL al endpoint del dashboard', () => {
    const { flushDashboard } = setup({ prop_id: '1', only_profitable: '1' });
    const req = flushDashboard() as ReturnType<typeof Object>;

    expect(req.request.params.get('only_profitable')).toBe('1');
  });

  it('por defecto NO pide only_profitable (todas las filas)', () => {
    const { flushDashboard } = setup({ prop_id: '1' });
    const req = flushDashboard() as ReturnType<typeof Object>;

    expect(req.request.params.get('only_profitable')).toBeNull();
  });

  it('el chip "Solo con ganancias" activa el filtro vía URL', async () => {
    const { el, router, flushDashboard } = setup({ prop_id: '1' });
    flushDashboard();

    const chip = Array.from(el.querySelectorAll<HTMLButtonElement>('button.rpd-chip'))
      .find((b) => b.textContent?.includes('Solo con ganancias'));
    expect(chip).toBeDefined();

    chip!.click();
    expect(router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({
        queryParams: expect.objectContaining({ only_profitable: '1' }),
        queryParamsHandling: 'merge',
      }),
    );
  });

  it('resalta las filas con ganancias y deja planas las de revenue 0', async () => {
    const { fixture, el, flushDashboard } = setup({ prop_id: '1' });
    flushDashboard();
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    fixture.detectChanges();

    const highlighted = el.querySelectorAll('tr.has-revenue');
    expect(highlighted.length).toBe(1);
    expect(highlighted[0].textContent).toContain('Habitación Deluxe');
  });

  it('"Limpiar" también apaga el filtro de ganancias', () => {
    const { el, router, flushDashboard } = setup({ prop_id: '1', only_profitable: '1' });
    flushDashboard();

    const clearBtn = el.querySelector<HTMLButtonElement>('.rpd-clear-btn');
    expect(clearBtn).not.toBeNull();
    clearBtn!.click();

    expect(router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({
        queryParams: expect.objectContaining({ only_profitable: null }),
        queryParamsHandling: 'merge',
      }),
    );
  });
});
