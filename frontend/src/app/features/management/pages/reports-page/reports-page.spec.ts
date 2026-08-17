import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../../../core/auth/auth.service';
import { ManagementReportsPageComponent } from './reports-page';

describe('ManagementReportsPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [ManagementReportsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(ManagementReportsPageComponent);
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

  it('incluye page en la URL del recurso', () => {
    const ctx = setup(true);

    ctx.component.page.set(3);
    const url = (ctx.component as unknown as { buildUrl(): string }).buildUrl();
    expect(url).toContain('page=3');
    expect(url).toContain('page_size=10');
  });

  it('goToPage cambia la página dentro de los límites', () => {
    const ctx = setup(true);

    const url = (ctx.component as unknown as { buildUrl(): string }).buildUrl();
    void url;
    ctx.component.goToPage(0);
    expect(ctx.component.page()).toBe(1);
    ctx.component.goToPage(99);
    expect(ctx.component.page()).toBe(1); // sin datos → se mantiene en 1
  });

  it('chartDatasets mapea la serie sin datos a lista vacía', () => {
    const ctx = setup(true);

    expect(ctx.component.chartDatasets()).toEqual([]);
    expect(ctx.component.chartLabels()).toEqual([]);
  });
});
