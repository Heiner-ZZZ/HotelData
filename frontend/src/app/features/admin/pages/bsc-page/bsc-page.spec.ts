import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../../../core/auth/auth.service';
import { BscPageComponent } from './bsc-page';

describe('BscPageComponent (gate de exportación)', () => {
  function setup(hasDownload: boolean) {
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;

    TestBed.configureTestingModule({
      imports: [BscPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(BscPageComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, auth };
  }

  it('oculta el botón de exportar sin reports.download', () => {
    const ctx = setup(false);

    expect(ctx.component.canExport()).toBe(false);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Exportar reporte');
  });

  it('muestra el botón de exportar con reports.download', () => {
    const ctx = setup(true);

    expect(ctx.component.canExport()).toBe(true);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Exportar reporte');
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup(true);

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
