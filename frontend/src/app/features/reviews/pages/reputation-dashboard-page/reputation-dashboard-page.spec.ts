import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ReviewsApiService } from '../../services/reviews-api.service';
import type { ReputationDashboard, ReviewAnalytics, ReviewAnalyticsRow } from '../../models/reviews.model';
import { ReputationDashboardPageComponent } from './reputation-dashboard-page';

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

function makeRow(overrides: Partial<ReviewAnalyticsRow> = {}): ReviewAnalyticsRow {
  return {
    date: '2026-08-20',
    propId: 1,
    reviews: 0,
    avgRating: 0,
    approved: 0,
    pending: 0,
    rejected: 0,
    responded: 0,
    positive: 0,
    neutral: 0,
    negative: 0,
    moderatedCount: 0,
    avgModerationMinutes: null,
    respondedCount: 0,
    avgResponseMinutes: null,
    ...overrides,
  };
}

/** Compuesto (ClickHouse kpi_review_daily): dos días con ventas… digo, reseñas. */
function makeAnalytics(rows: ReviewAnalyticsRow[] = []): ReviewAnalytics {
  return { available: true, days: 30, rows };
}

/** Simple (Mongo reviews): recientes para el aside. */
function makeMongo(overrides: Partial<ReputationDashboard> = {}): ReputationDashboard {
  return {
    gri: 72, griTarget: 90, griChange: 1.2, totalReviews: 5,
    departmental: [],
    recentFeedback: [
      { id: 'R1', userName: 'María Gómez', rating: 5, comment: 'Excelente estadía', createdAt: '2026-08-21T10:00:00' },
    ],
    dailyCounts: [],
    ...overrides,
  };
}

const DEFAULT_ROWS = (): ReviewAnalyticsRow[] => [
  // d1: 3 reseñas aprobadas con rating medio 4 → aporta 12 al numerador.
  makeRow({
    date: '2026-08-20', reviews: 3, approved: 3, avgRating: 4,
    responded: 2, respondedCount: 2, avgResponseMinutes: 60,
    positive: 2, neutral: 1, negative: 0,
    pending: 0, rejected: 0, moderatedCount: 2, avgModerationMinutes: 30,
  }),
  // d2: 1 aprobada rating 2, 2 pendientes.
  makeRow({
    date: '2026-08-21', reviews: 2, approved: 1, avgRating: 2,
    responded: 0, respondedCount: 0, avgResponseMinutes: null,
    positive: 0, neutral: 0, negative: 1,
    pending: 2, rejected: 0, moderatedCount: 0, avgModerationMinutes: null,
  }),
];

describe('ReputationDashboardPageComponent — patrón Z', () => {
  let navigate: jest.Mock;
  let mockApi: Record<string, jest.Mock>;

  beforeEach(async () => {
    navigate = jest.fn();
    mockApi = {
      getReputationAnalytics: jest.fn(() => of(makeAnalytics(DEFAULT_ROWS()))),
      getReputationDashboard: jest.fn(() => of(makeMongo())),
    };

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });
    TestBed.overrideComponent(KpiChartComponent, {
      set: { template: '<span>kpi-stub</span>' },
    });

    await TestBed.configureTestingModule({
      imports: [ReputationDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1', prop_label: 'Hotel Lima Centro' }) },
            queryParamMap: of(convertToParamMap({ prop_id: '1', prop_label: 'Hotel Lima Centro' })),
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
        { provide: AuthService, useValue: { hasPermission: () => true } },
        { provide: ReviewsApiService, useValue: mockApi },
      ],
    }).compileComponents();
  });

  function setup(query: Record<string, string> = {}) {
    if (Object.keys(query).length) {
      const qp = convertToParamMap(query);
      const route = TestBed.inject(ActivatedRoute) as any;
      route.snapshot = { ...route.snapshot, queryParamMap: qp };
      route.queryParamMap = of(qp);
    }
    const fixture = TestBed.createComponent(ReputationDashboardPageComponent);
    fixture.detectChanges();
    return { fixture, el: fixture.nativeElement as HTMLElement, router: TestBed.inject(Router) as unknown as jest.Mocked<Router> };
  }

  it('los KPIs salen del compuesto ClickHouse (total, GRI %, tasa de respuesta, respuesta media)', () => {
    const { el } = setup();

    const kpis = el.querySelectorAll('.repd-kpi');
    expect(kpis.length).toBeGreaterThanOrEqual(4);

    const text = el.querySelector('.repd-kpis')?.textContent ?? '';
    // Σreviews = 5 · GRI = ((4·3 + 2·1)/4)/5·100 = 70 · tasa respuesta = 2/5 = 40% · media 60 min
    expect(text).toContain('5');
    expect(text).toContain('70');
    expect(text).toContain('40');
    expect(mockApi.getReputationAnalytics).toHaveBeenCalled();
  });

  it('la tabla de detalle diario lista las filas del compuesto con su paginación', () => {
    const { el } = setup();

    const meta = el.querySelector('.repd-meta')?.textContent ?? '';
    expect(meta).toContain('2 fila(s)');
    expect(el.querySelectorAll('.repd-table tbody tr').length).toBe(2);
    expect(el.textContent).toContain('2026-08-20');
  });

  it('pagina client-side cuando hay más de una página de días', () => {
    // Genero 25 días → pageSize 20 → 2 páginas.
    const manyRows = Array.from({ length: 25 }, (_, i) =>
      makeRow({ date: `2026-08-${String((i % 28) + 1).padStart(2, '0')}`, reviews: i + 1, approved: 1, avgRating: 4 }),
    );
    mockApi.getReputationAnalytics.mockReturnValue(of(makeAnalytics(manyRows)));

    const { fixture, el } = setup();
    fixture.detectChanges();

    expect(el.querySelector('.repd-meta')?.textContent).toContain('Pág. 1 de 2');

    const next = Array.from(el.querySelectorAll<HTMLButtonElement>('.repd-page-btn'))
      .find((b) => !b.disabled && b.textContent?.includes('Siguiente'));
    next?.click();
    fixture.detectChanges();

    expect(el.querySelectorAll('.repd-table tbody tr').length).toBe(5);
    expect(el.querySelector('.repd-meta')?.textContent).toContain('Pág. 2 de 2');
  });

  it('muestra la distribución de sentimiento agregada (positivo/neutral/negativo)', () => {
    const { el } = setup();

    const aside = el.querySelector('.repd-sentiment')?.textContent ?? '';
    expect(aside).toContain('Positivo');
    expect(aside).toContain('Negativo');
    // Σ positivo = 2, negativo = 1.
    expect(aside).toContain('2');
    expect(aside).toContain('1');
  });

  it('conserva las reseñas recientes del informe simple (Mongo)', () => {
    const { el } = setup();

    const aside = el.querySelector('.repd-recent')?.textContent ?? '';
    expect(aside).toContain('María Gómez');
    expect(mockApi.getReputationDashboard).toHaveBeenCalledWith(1, 30);
  });

  it('el chip de período navega con ?days=N (URL-driven como el resto de informes)', () => {
    const { el, router } = setup();

    const chip = Array.from(el.querySelectorAll<HTMLButtonElement>('button.repd-chip'))
      .find((b) => b.textContent?.includes('7 días'));
    chip?.click();

    expect(router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({
        queryParams: expect.objectContaining({ days: 7 }),
        queryParamsHandling: 'merge',
      }),
    );
  });

  it('cuando el compuesto no está disponible muestra el mensaje del DAG en vez de la grilla', () => {
    mockApi.getReputationAnalytics.mockReturnValue(
      of({ available: false, days: 30, rows: [], message: 'El DAG horario todavía no ha cargado kpi_review_daily.' }),
    );
    const { el } = setup();

    expect(el.textContent).toContain('El DAG horario todavía no ha cargado');
  });
});

describe('ReputationDashboardPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.overrideComponent(PropertySelectorComponent, {
      set: { template: '<span>selector-stub</span>' },
    });
    TestBed.overrideComponent(KpiChartComponent, {
      set: { template: '<span>kpi-stub</span>' },
    });

    TestBed.configureTestingModule({
      imports: [ReputationDashboardPageComponent],
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
          useValue: { events: new Subject<unknown>().asObservable(), navigate: jest.fn(), routerState: { snapshot: { root: { data: {}, firstChild: null } } } },
        },
        {
          provide: PropertyContextService,
          useValue: {
            currentPropId: signal(1),
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
        { provide: AuthService, useValue: auth },
        {
          provide: ReviewsApiService,
          useValue: {
            getReputationAnalytics: jest.fn(() => of(makeAnalytics(DEFAULT_ROWS()))),
            getReputationDashboard: jest.fn(() => of(makeMongo())),
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(ReputationDashboardPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('oculta los botones de exportar sin reports.download', () => {
    const ctx = setup(false);

    expect(ctx.component.canExport()).toBe(false);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Exportar PDF');
    expect(el.textContent).not.toContain('Exportar Excel');
  });

  it('muestra los botones de exportar con reports.download', () => {
    const ctx = setup(true);

    expect(ctx.component.canExport()).toBe(true);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Exportar PDF');
    expect(el.textContent).toContain('Exportar Excel');
  });
});
