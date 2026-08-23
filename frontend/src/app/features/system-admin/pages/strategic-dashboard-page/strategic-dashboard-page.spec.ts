import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

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
