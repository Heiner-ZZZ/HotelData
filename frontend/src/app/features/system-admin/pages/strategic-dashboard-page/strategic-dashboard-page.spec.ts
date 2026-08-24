import { HttpBackend, HttpResponse, provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { StrategicDashboardPageComponent } from './strategic-dashboard-page';

describe('StrategicDashboardPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean, initialUrl = '/') {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      currentUser: jest.fn(() => ({ primaryRole: 'super_admin' })),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;
    const toast = { show: jest.fn() } as unknown as ToastService;

    TestBed.configureTestingModule({
      imports: [StrategicDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([
          { path: 'informes-estrategicos', component: StrategicDashboardPageComponent },
          { path: 'informes-estrategicos/:report', component: StrategicDashboardPageComponent },
          { path: 'management/informes-estrategicos', component: StrategicDashboardPageComponent },
          { path: 'management/informes-estrategicos/:report', component: StrategicDashboardPageComponent },
          { path: '**', component: StrategicDashboardPageComponent },
        ]),
        { provide: AuthService, useValue: auth },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(StrategicDashboardPageComponent);
    const router = TestBed.inject(Router);
    if (initialUrl !== '/') {
      void router.navigateByUrl(initialUrl);
    }
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth, toast, router };
  }

  it('deshabilita la exportación sin reports.download', () => {
    const ctx = setup(false);

    expect(ctx.component.canExport()).toBe(false);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Exportar CSV');
  });

  it('habilita la exportación con reports.download', () => {
    const ctx = setup(true);

    expect(ctx.component.canExport()).toBe(true);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Exportar CSV');
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });

  it('no exporta el CSV del informe activo sin datos cargados', () => {
    const ctx = setup(true);

    expect(() => ctx.component.exportCsv()).not.toThrow();
    expect(ctx.toast.show).not.toHaveBeenCalled();
  });

  it('decide Vista B en la ruta del sistema (/informes-estrategicos)', async () => {
    const ctx = setup(true, '/informes-estrategicos');
    await ctx.router.navigateByUrl('/informes-estrategicos');

    expect(ctx.component.isPortfolioView()).toBe(true);
    expect(ctx.component.headerEyebrow()).toContain('VISTA B');
    expect(ctx.component.headerTitle()).toBe('Control global de la cartera');
  });

  it('decide Vista A en la ruta de gestión (/management/informes-estrategicos)', async () => {
    const ctx = setup(true, '/management/informes-estrategicos');
    await ctx.router.navigateByUrl('/management/informes-estrategicos');

    expect(ctx.component.isPortfolioView()).toBe(false);
    expect(ctx.component.headerEyebrow()).toContain('VISTA A');
    expect(ctx.component.headerTitle()).toBe('Cómo crecer este hotel');
  });

  it('el informe activo del menú horizontal se deriva del segmento de ruta', async () => {
    const ctx = setup(true, '/informes-estrategicos/g03');
    await ctx.router.navigateByUrl('/informes-estrategicos/g03');

    expect(ctx.component.report()).toBe('g03');
    expect(ctx.component.activeReportSlug()).toBe('sistema.informes-estrategicos.g03');
  });

  it('el menú horizontal de Vista A resuelve el slug de IE-H02', async () => {
    const ctx = setup(true, '/management/informes-estrategicos/h02');
    await ctx.router.navigateByUrl('/management/informes-estrategicos/h02');

    expect(ctx.component.report()).toBe('h02');
    expect(ctx.component.activeReportSlug()).toBe('gestion.informes-estrategicos.h02');
  });

  it('report inválido cae al primer informe de la vista', async () => {
    const ctx = setup(true, '/informes-estrategicos/zzz');
    await ctx.router.navigateByUrl('/informes-estrategicos/zzz');

    expect(ctx.component.report()).toBe('g01');
    expect(ctx.component.activeReportSlug()).toBe('sistema.informes-estrategicos.g01');
  });

  it('el drill-down de cartera navega a la Vista A del hotel (IE-H01)', () => {
    const ctx = setup(true);
    const navigateSpy = jest.spyOn(ctx.router, 'navigate');

    ctx.component.goToHotel(7, 'Hotel Lima Centro');

    expect(navigateSpy).toHaveBeenCalledWith(['/management/informes-estrategicos', 'h01'], {
      queryParams: { prop_id: '7', prop_label: 'Hotel Lima Centro' },
      queryParamsHandling: 'merge',
    });
  });

  it('expone los computeds de IE-G02 (rankings) e IE-H02 (posicionamiento Z) vacíos sin datos', () => {
    const ctx = setup(true);

    expect(ctx.component.rankingGroups()).toEqual([]);
    expect(ctx.component.rankingsKpis()).toEqual([]);
    expect(ctx.component.rankingsChartDatasets()).toEqual([]);
    expect(ctx.component.posicionamientoKpis()).toEqual([]);
    expect(ctx.component.posicionamientoRows()).toEqual([]);
    expect(ctx.component.posicionamientoSerieDatasets()).toEqual([]);
  });

  it('toggleMap y hasMapCoords controlan el mapa competitivo de IE-H02', () => {
    const ctx = setup(true);

    expect(ctx.component.mapOpen()).toBe(false);
    expect(ctx.component.hasMapCoords({ ownLat: null, ownLng: null })).toBe(false);
    expect(ctx.component.hasMapCoords({ ownLat: -12.0464, ownLng: -77.0428 })).toBe(true);

    ctx.component.toggleMap();
    expect(ctx.component.mapOpen()).toBe(true);
    ctx.component.toggleMap();
    expect(ctx.component.mapOpen()).toBe(false);
  });

  // ── Exportación por informe seccionado (g01..g05 / h01/h02) ────────────

  it.each([
    ['h01', 'IE-H01 · Desempeño y planes'],
    ['h02', 'IE-H02 · Posicionamiento local'],
    ['g01', 'IE-G01 · KPIs de cartera'],
    ['g02', 'IE-G02 · Rankings estratégicos'],
    ['g03', 'IE-G03 · Rentabilidad de la cartera'],
    ['g04', 'IE-G04 · Mapa de mercados'],
    ['g05', 'IE-G05 · Forecasting'],
  ])('etiqueta de exportación del informe %s', async (report, label) => {
    const view = report.startsWith('g') ? 'informes-estrategicos' : 'management/informes-estrategicos';
    const ctx = setup(true, `/${view}/${report}`);
    await ctx.router.navigateByUrl(`/${view}/${report}`);

    expect(ctx.component.report()).toBe(report);
    expect(ctx.component.reportExportLabel()).toBe(label);
  });

  it('deshabilita el CSV de IE-G05 (placeholder, sin datos exportables)', async () => {
    const ctx = setup(true, '/informes-estrategicos/g05');
    await ctx.router.navigateByUrl('/informes-estrategicos/g05');

    expect(ctx.component.exportDisabled()).toBe(true);
  });

  it.each(['h01', 'h02', 'g01', 'g02', 'g03', 'g04'])(
    'deshabilita el CSV de %s mientras no hay datos cargados',
    async (report) => {
      const view = report.startsWith('g') ? 'informes-estrategicos' : 'management/informes-estrategicos';
      const ctx = setup(true, `/${view}/${report}`);
      await ctx.router.navigateByUrl(`/${view}/${report}`);

      expect(ctx.component.exportDisabled()).toBe(true);
    },
  );

  it('deshabilita el CSV sin reports.download incluso en informes con datos', () => {
    const ctx = setup(false);

    expect(ctx.component.exportDisabled()).toBe(true);
  });

  it('exportCsv despacha al informe activo sin datos (no-op seguro)', async () => {
    const ctx = setup(true, '/informes-estrategicos/g03');
    await ctx.router.navigateByUrl('/informes-estrategicos/g03');

    expect(() => ctx.component.exportCsv()).not.toThrow();
    expect(ctx.toast.show).not.toHaveBeenCalled();
  });
});

// ─── Layout IE-H01 en pantallas 15.6" (patrón Z) ─────────────────────────
// El dueño pidió: KPIs arriba, DOS gráficos lado a lado y las DOS tablas de
// registros al final, APILADAS una debajo de la otra (con mínimo 5 filas por
// página para que la última tabla no quede oculta). Antes el gráfico de la
// serie iba solo (dejaba un hueco 1fr) y la tabla de planes quedaba
// comprimida a 1fr junto al gráfico de planes → caja "Rentabilidad por plan"
// ajustadísima.

describe('StrategicDashboardPageComponent (layout IE-H01, 15.6")', () => {
  function layoutBackend() {
    const emptyPlanes = { rows: [], total: 0, page: 1, page_size: 20, total_pages: 1, has_next: false, has_prev: false };
    const hotelDto = {
      available: true,
      source: 'clickhouse',
      date_from: '2026-06-01',
      date_to: '2026-08-24',
      prop_id: 1,
      summary: {
        kpis: [{
          id: 'revenue', label: 'Revenue neto', value: 2943.4, unit: 'USD',
          target: null, pct_change: 85.15, has_prev: true, trend: 'up',
          semaforo: 'green', detail: '12 reservas en el período',
        }],
        hoteles: 1,
        posicionamiento: null,
      },
      serie: { labels: ['jun 2026', 'jul 2026', 'ago 2026'], datasets: [] },
      posicionamiento_serie: { labels: [], datasets: [] },
      posicionamiento_rows: [],
      // El backend manda ``rows`` como ARRAY + paginación top-level, y ``planes``
      // como objeto paginado con filas anidadas (shape real del contrato).
      rows: [],
      total: 0, page: 1, page_size: 20, total_pages: 1, has_next: false, has_prev: false,
      planes: emptyPlanes,
    };
    return {
      handle: (req: HttpRequest<unknown>) => {
        const url = String(req.url);
        if (url.includes('/management/properties/context')) {
          return of(new HttpResponse({ status: 200, body: { mode: 'all', assigned_properties: [], default_prop_id: 0 } }));
        }
        if (url.includes('/api/strategic/hotel/')) {
          return of(new HttpResponse({ status: 200, body: hotelDto }));
        }
        // Cualquier otra petición (ej. property-selector) con forma vacía segura.
        return of(new HttpResponse({ status: 200, body: { properties: [] } }));
      },
    };
  }

  function setupLayout() {
    // jsdom no expone matchMedia; ThemeService (inyectado por app-kpi-chart) lo necesita.
    window.matchMedia = (window.matchMedia ??
      (() => ({
        matches: false, media: '', onchange: null,
        addListener: () => {}, removeListener: () => {},
        addEventListener: () => {}, removeEventListener: () => {}, dispatchEvent: () => false,
      }))) as unknown as typeof window.matchMedia;

    const auth = {
      hasPermission: jest.fn(() => true),
      currentUser: jest.fn(() => ({ primaryRole: 'super_admin' })),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;
    const toast = { show: jest.fn() } as unknown as ToastService;

    TestBed.configureTestingModule({
      imports: [StrategicDashboardPageComponent],
      providers: [
        provideHttpClient(),
        provideRouter([
          { path: 'management/informes-estrategicos/:report', component: StrategicDashboardPageComponent },
          { path: '**', component: StrategicDashboardPageComponent },
        ]),
        { provide: HttpBackend, useValue: layoutBackend() },
        { provide: AuthService, useValue: auth },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(StrategicDashboardPageComponent);
    const router = TestBed.inject(Router);
    return { fixture, router };
  }

  it('IE-H01: los dos gráficos van lado a lado (serie + revenue por plan)', async () => {
    const { fixture, router } = setupLayout();
    await router.navigateByUrl('/management/informes-estrategicos/h01?prop_id=1&prop_label=Hotel');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.componentInstance.hotel()).not.toBeNull();

    const el: HTMLElement = fixture.nativeElement;
    const chartsRow = el.querySelector('.strd-chart-row.charts');
    expect(chartsRow).not.toBeNull();
    expect(chartsRow!.querySelectorAll('app-kpi-chart').length).toBe(2);
  });

  it('IE-H01: las dos tablas de registros van al final, apiladas una debajo de la otra', async () => {
    const { fixture, router } = setupLayout();
    await router.navigateByUrl('/management/informes-estrategicos/h01?prop_id=1&prop_label=Hotel');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.componentInstance.hotel()).not.toBeNull();

    const el: HTMLElement = fixture.nativeElement;
    const tableGrid = el.querySelector('.strd-table-grid');
    expect(tableGrid).not.toBeNull();
    expect(tableGrid!.querySelectorAll('.strd-table-card').length).toBe(2);
  });

  it('IE-H01: los gráficos se renderizan antes que las tablas (patrón Z)', async () => {
    const { fixture, router } = setupLayout();
    await router.navigateByUrl('/management/informes-estrategicos/h01?prop_id=1&prop_label=Hotel');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.componentInstance.hotel()).not.toBeNull();

    const el: HTMLElement = fixture.nativeElement;
    const sections = Array.from(el.querySelectorAll('section'));
    const chartsIdx = sections.findIndex((s) => s.classList.contains('strd-chart-row'));
    const tablesIdx = sections.findIndex((s) => s.classList.contains('strd-table-grid'));
    expect(chartsIdx).toBeGreaterThanOrEqual(0);
    expect(tablesIdx).toBeGreaterThan(chartsIdx);
  });
});
